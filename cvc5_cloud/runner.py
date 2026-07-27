#!/usr/bin/env python3
"""Race cvc5 configurations locally or across SSH workers."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import enum
import hashlib
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from typing import Iterable, Sequence, TextIO


class Result(enum.Enum):
    UNKNOWN = "unknown"
    SAT = "sat"
    UNSAT = "unsat"

    @property
    def exit_code(self) -> int:
        return {Result.UNKNOWN: 0, Result.SAT: 10, Result.UNSAT: 20}[self]


class Mode(enum.Enum):
    SEQUENTIAL = "sequential"
    PORTFOLIO = "portfolio"
    DISTRIBUTED = "distributed"


@dataclasses.dataclass(frozen=True)
class ProcessSpec:
    label: str
    command: tuple[str, ...]
    host: str | None = None


@dataclasses.dataclass
class RunningProcess:
    spec: ProcessSpec
    process: subprocess.Popen[str]
    stdout: TextIO
    stderr: TextIO

    def close_output(self) -> None:
        self.stdout.close()
        self.stderr.close()


@dataclasses.dataclass(frozen=True)
class RaceConfig:
    cvc5: Path
    formula: Path
    timeout_seconds: float
    mode: Mode = Mode.DISTRIBUTED
    jobs_per_node: int = 0
    local_replicas: int = 1
    hosts: tuple[str, ...] = ()
    ssh_user: str | None = None
    extra_cvc5_args: tuple[str, ...] = ()
    shutdown_grace_seconds: float = 3.0


SSH_OPTIONS = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=5",
    "-o",
    "ConnectionAttempts=1",
    "-o",
    "ServerAliveInterval=5",
    "-o",
    "ServerAliveCountMax=2",
)


def parse_solver_result(output: str) -> Result:
    """Return the last exact SMT-LIB result in a solver output stream."""
    for line in reversed(output.splitlines()):
        normalized = line.strip().lower()
        if normalized in ("sat", "s satisfiable"):
            return Result.SAT
        if normalized in ("unsat", "s unsatisfiable"):
            return Result.UNSAT
        if normalized in ("unknown", "s unknown", "c unknown"):
            return Result.UNKNOWN
    return Result.UNKNOWN


def physical_core_count() -> int:
    """Best-effort physical core count, with a conservative fallback."""
    try:
        output = subprocess.check_output(
            ["lscpu", "--parse=CORE,SOCKET"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        cores = {
            line.strip()
            for line in output.splitlines()
            if line.strip() and not line.startswith("#")
        }
        if cores:
            return len(cores)
    except (OSError, subprocess.SubprocessError):
        pass
    logical = os.cpu_count() or 1
    return max(1, logical // 2)


def build_cvc5_command(
    cvc5: Path,
    formula: Path | str,
    timeout_seconds: float,
    *,
    portfolio: bool,
    jobs: int,
    seed: int | None,
    extra_args: Sequence[str] = (),
) -> tuple[str, ...]:
    """Construct one cvc5 invocation."""
    tlimit_ms = max(1, int(timeout_seconds * 1000))
    command = [
        str(cvc5),
        "--lang=smt2",
        f"--tlimit={tlimit_ms}",
    ]
    if portfolio:
        command.extend(("--use-portfolio", f"--portfolio-jobs={jobs}"))
    if seed is not None:
        command.extend((f"--seed={seed}", f"--sat-random-seed={seed}"))
    command.extend(extra_args)
    command.append(str(formula))
    return tuple(command)


def _host_target(host: str, ssh_user: str | None) -> str:
    return f"{ssh_user}@{host}" if ssh_user else host


def _remote_formula_path(formula: Path) -> str:
    identity = f"{formula.resolve()}:{os.getpid()}:{time.time_ns()}".encode()
    token = hashlib.sha256(identity).hexdigest()[:20]
    return f"/tmp/cvc5-cloud-{token}.smt2"


def _stage_formula(
    host: str,
    ssh_user: str | None,
    formula: Path,
    remote_path: str,
    deadline: float,
) -> tuple[str, str | None]:
    target = _host_target(host, ssh_user)
    command = ["scp", "-q", *SSH_OPTIONS, str(formula), f"{target}:{remote_path}"]
    timeout_seconds = max(0.1, deadline - time.monotonic())
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return host, str(error)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"scp exited {completed.returncode}"
        return host, detail
    return host, None


def _stage_remote_formulas(
    hosts: Sequence[str],
    ssh_user: str | None,
    formula: Path,
    remote_path: str,
    deadline: float,
) -> tuple[str, ...]:
    if not hosts:
        return ()
    workers = min(32, len(hosts))
    successful: set[str] = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _stage_formula,
                host,
                ssh_user,
                formula,
                remote_path,
                deadline,
            )
            for host in hosts
        ]
        for future in concurrent.futures.as_completed(futures):
            host, error = future.result()
            if error is None:
                successful.add(host)
            else:
                print(f"[cvc5-cloud] skipping worker {host}: {error}", file=sys.stderr)
    return tuple(host for host in hosts if host in successful)


def _build_process_specs(config: RaceConfig, deadline: float) -> list[ProcessSpec]:
    jobs = config.jobs_per_node or min(8, physical_core_count())
    solve_seconds = max(
        0.1,
        deadline - time.monotonic() - config.shutdown_grace_seconds,
    )

    if config.mode is Mode.SEQUENTIAL:
        command = build_cvc5_command(
            config.cvc5,
            config.formula,
            solve_seconds,
            portfolio=False,
            jobs=1,
            seed=None,
            extra_args=config.extra_cvc5_args,
        )
        return [ProcessSpec("local-sequential", command)]

    if config.mode is Mode.PORTFOLIO:
        command = build_cvc5_command(
            config.cvc5,
            config.formula,
            solve_seconds,
            portfolio=True,
            jobs=jobs,
            seed=None,
            extra_args=config.extra_cvc5_args,
        )
        return [ProcessSpec("local-portfolio", command)]

    remote_path = _remote_formula_path(config.formula)
    ready_hosts = _stage_remote_formulas(
        config.hosts,
        config.ssh_user,
        config.formula,
        remote_path,
        deadline - config.shutdown_grace_seconds,
    )
    solve_seconds = max(
        0.1,
        deadline - time.monotonic() - config.shutdown_grace_seconds,
    )

    specs: list[ProcessSpec] = []
    seed = 1
    for replica in range(config.local_replicas):
        command = build_cvc5_command(
            config.cvc5,
            config.formula,
            solve_seconds,
            portfolio=True,
            jobs=jobs,
            seed=seed,
            extra_args=config.extra_cvc5_args,
        )
        specs.append(ProcessSpec(f"local-{replica}", command))
        seed += 1

    for host in ready_hosts:
        solver_command = build_cvc5_command(
            config.cvc5,
            remote_path,
            solve_seconds,
            portfolio=True,
            jobs=jobs,
            seed=seed,
            extra_args=config.extra_cvc5_args,
        )
        target = _host_target(host, config.ssh_user)
        remote_command = f"exec {shlex.join(solver_command)}"
        specs.append(
            ProcessSpec(
                f"ssh-{host}",
                ("ssh", "-T", *SSH_OPTIONS, target, remote_command),
                host=host,
            )
        )
        seed += 1
    return specs


def _start_process(spec: ProcessSpec) -> RunningProcess:
    stdout = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    stderr = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    try:
        process = subprocess.Popen(
            spec.command,
            stdout=stdout,
            stderr=stderr,
            text=True,
            start_new_session=True,
        )
    except OSError:
        stdout.close()
        stderr.close()
        raise
    return RunningProcess(spec, process, stdout, stderr)


def _collect_process(running: RunningProcess) -> tuple[str, str, int]:
    return_code = running.process.wait()
    running.stdout.seek(0)
    running.stderr.seek(0)
    return running.stdout.read(), running.stderr.read(), return_code


def _terminate_processes(
    processes: Iterable[RunningProcess],
    grace_seconds: float,
) -> None:
    all_processes = list(processes)
    for running in all_processes:
        try:
            os.killpg(running.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    end = time.monotonic() + max(0.0, grace_seconds)
    for running in all_processes:
        if running.process.poll() is not None:
            continue
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        try:
            running.process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            pass
    for running in all_processes:
        try:
            os.killpg(running.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_race(config: RaceConfig) -> Result:
    """Run the configured baseline and return the first definitive result."""
    if config.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if config.jobs_per_node < 0:
        raise ValueError("jobs_per_node cannot be negative")
    if config.local_replicas < 1:
        raise ValueError("local_replicas must be at least one")
    if config.shutdown_grace_seconds < 0:
        raise ValueError("shutdown_grace_seconds cannot be negative")
    if not config.cvc5.is_file():
        raise FileNotFoundError(f"cvc5 binary not found: {config.cvc5}")
    if not config.formula.is_file():
        raise FileNotFoundError(f"formula not found: {config.formula}")

    deadline = time.monotonic() + config.timeout_seconds
    specs = _build_process_specs(config, deadline)
    if not specs:
        return Result.UNKNOWN

    displayed_jobs = (
        1
        if config.mode is Mode.SEQUENTIAL
        else config.jobs_per_node or min(8, physical_core_count())
    )
    print(
        f"[cvc5-cloud] mode={config.mode.value} nodes={len(specs)} "
        f"jobs-per-node={displayed_jobs}",
        file=sys.stderr,
    )
    running: list[RunningProcess] = []
    try:
        for spec in specs:
            running.append(_start_process(spec))
    except OSError:
        _terminate_processes(running, config.shutdown_grace_seconds)
        for process in running:
            process.close_output()
        raise

    winner = Result.UNKNOWN
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(running))
    futures = {
        pool.submit(_collect_process, process): process for process in running
    }
    pending = set(futures)
    try:
        while pending and time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            done, pending = concurrent.futures.wait(
                pending,
                timeout=remaining,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done:
                break
            for future in done:
                process = futures[future]
                try:
                    stdout, stderr, return_code = future.result()
                except Exception as error:
                    print(
                        f"[cvc5-cloud] {process.spec.label} failed: {error}",
                        file=sys.stderr,
                    )
                    continue
                result = parse_solver_result(stdout)
                if result is Result.UNKNOWN and return_code in (10, 20):
                    result = Result.SAT if return_code == 10 else Result.UNSAT
                if result in (Result.SAT, Result.UNSAT):
                    print(
                        f"[cvc5-cloud] winner={process.spec.label} "
                        f"result={result.value}",
                        file=sys.stderr,
                    )
                    winner = result
                    return winner
                if return_code not in (0, 10, 20):
                    detail = stderr.strip().splitlines()
                    suffix = f": {detail[-1]}" if detail else ""
                    print(
                        f"[cvc5-cloud] {process.spec.label} exited "
                        f"{return_code}{suffix}",
                        file=sys.stderr,
                    )
        return winner
    finally:
        _terminate_processes(running, config.shutdown_grace_seconds)
        pool.shutdown(wait=True, cancel_futures=True)
        for process in running:
            process.close_output()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formula", type=Path)
    parser.add_argument("--cvc5", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in Mode],
        default=Mode.DISTRIBUTED.value,
    )
    parser.add_argument("--timeout-seconds", type=float, default=200.0)
    parser.add_argument(
        "--jobs-per-node",
        type=int,
        default=0,
        help="cvc5 portfolio jobs per node; 0 auto-detects up to 8",
    )
    parser.add_argument(
        "--local-replicas",
        type=int,
        default=1,
        help="seeded local replicas in distributed mode",
    )
    parser.add_argument("--host", action="append", default=[], dest="hosts")
    parser.add_argument("--ssh-user")
    parser.add_argument(
        "--cvc5-arg",
        action="append",
        default=[],
        dest="cvc5_args",
        help="additional argument forwarded to every cvc5 process",
    )
    parser.add_argument(
        "--shutdown-grace-seconds",
        type=float,
        default=3.0,
        help="reserve this much of the harness timeout for process cleanup",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = RaceConfig(
        cvc5=args.cvc5,
        formula=args.formula,
        timeout_seconds=args.timeout_seconds,
        mode=Mode(args.mode),
        jobs_per_node=args.jobs_per_node,
        local_replicas=args.local_replicas,
        hosts=tuple(args.hosts),
        ssh_user=args.ssh_user,
        extra_cvc5_args=tuple(args.cvc5_args),
        shutdown_grace_seconds=args.shutdown_grace_seconds,
    )
    try:
        result = run_race(config)
    except (OSError, ValueError) as error:
        print(f"[cvc5-cloud] error: {error}", file=sys.stderr)
        return 1
    print(result.value, flush=True)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
