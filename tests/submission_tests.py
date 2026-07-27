#!/usr/bin/env python3
"""Score the current submission on the fixed cvc5 training suite."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cvc5_cloud.configuration import SolverConfig, load_config, read_logic
from cvc5_cloud.runner import Mode, RaceConfig, Result, run_race


@dataclasses.dataclass(frozen=True)
class Case:
    formula: Path
    relative: Path
    logic: str
    expected: Result


@dataclasses.dataclass(frozen=True)
class Run:
    case: Case
    result: Result
    wall_seconds: float
    error: str | None
    diagnostics: str

    @property
    def correct(self) -> bool:
        return self.result is self.case.expected

    @property
    def wrong(self) -> bool:
        return self.result in (Result.SAT, Result.UNSAT) and not self.correct


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases(
    benchmark_root: Path,
    selected_logics: set[str],
    limit: int | None,
) -> list[Case]:
    manifest_path = benchmark_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
        entries = manifest["benchmarks"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        message = f"invalid benchmark manifest {manifest_path}: {error}"
        raise ValueError(message) from error
    if not isinstance(entries, list):
        raise ValueError(f"invalid benchmark list in {manifest_path}")

    cases: list[Case] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"invalid benchmark entry in {manifest_path}")
        try:
            relative = Path(entry["path"])
            logic = str(entry["logic"]).upper()
            expected = Result(str(entry["status"]).lower())
            expected_hash = str(entry["sha256"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid benchmark entry: {entry!r}") from error
        if expected not in (Result.SAT, Result.UNSAT):
            raise ValueError(f"benchmark status must be sat or unsat: {relative}")
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"benchmark path escapes its suite: {relative}")
        if selected_logics and logic not in selected_logics:
            continue

        formula = benchmark_root / relative
        if not formula.is_file():
            raise ValueError(f"missing benchmark: {formula}")
        actual_hash = sha256(formula)
        if actual_hash != expected_hash:
            raise ValueError(
                f"benchmark checksum mismatch for {relative}: "
                f"{actual_hash} != {expected_hash}"
            )
        formula_logic = read_logic(formula)
        if formula_logic != logic:
            raise ValueError(
                f"logic mismatch for {relative}: {formula_logic} != {logic}"
            )
        cases.append(Case(formula, relative, logic, expected))

    cases.sort(key=lambda case: (case.logic, str(case.relative)))
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        suffix = f" for {sorted(selected_logics)}" if selected_logics else ""
        raise ValueError(f"no benchmarks selected from {benchmark_root}{suffix}")
    return cases


def cvc5_version(binary: Path) -> str:
    completed = subprocess.run(
        [str(binary), "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.strip().splitlines()
    return output[0] if output else "unknown"


def run_case(
    case: Case,
    config: SolverConfig,
    cvc5: Path,
    timeout: float,
) -> Run:
    diagnostics = io.StringIO()
    error: str | None = None
    started = time.perf_counter()
    try:
        with contextlib.redirect_stderr(diagnostics):
            result = run_race(
                RaceConfig(
                    cvc5=cvc5,
                    formula=case.formula,
                    timeout_seconds=timeout,
                    mode=Mode(config.mode),
                    jobs_per_node=config.jobs_per_node,
                    local_replicas=config.local_replicas,
                    extra_cvc5_args=config.cvc5_args,
                    shutdown_grace_seconds=min(0.5, timeout / 10),
                )
            )
    except Exception as exception:
        result = Result.UNKNOWN
        error = f"{type(exception).__name__}: {exception}"
    wall_seconds = min(time.perf_counter() - started, timeout)
    return Run(case, result, wall_seconds, error, diagnostics.getvalue())


def outcome(run: Run) -> str:
    if run.error:
        return "ERROR"
    if run.correct:
        return "PASS"
    if run.wrong:
        return "WRONG"
    return "UNKNOWN"


def print_summary(runs: list[Run], timeout: float) -> None:
    correct = sum(run.correct for run in runs)
    wrong = sum(run.wrong for run in runs)
    unknown = sum(run.result is Result.UNKNOWN for run in runs)
    errors = sum(run.error is not None for run in runs)
    wall = sum(run.wall_seconds for run in runs)
    par2 = sum(run.wall_seconds if run.correct else 2 * timeout for run in runs)

    print()
    print("Logic          Solved  Wrong  Unknown")
    print("-------------  ------  -----  -------")
    for logic in sorted({run.case.logic for run in runs}):
        selected = [run for run in runs if run.case.logic == logic]
        logic_correct = sum(run.correct for run in selected)
        logic_wrong = sum(run.wrong for run in selected)
        logic_unknown = sum(run.result is Result.UNKNOWN for run in selected)
        print(
            f"{logic:13s}  {logic_correct:2d}/{len(selected):<2d}"
            f"  {logic_wrong:5d}  {logic_unknown:7d}"
        )

    print()
    print(f"Score:      {correct}/{len(runs)} ({100 * correct / len(runs):.2f}%)")
    print(f"Wrong:      {wrong}")
    print(f"Unknown:    {unknown}")
    print(f"Errors:     {errors}")
    print(f"Wall time:  {wall:.3f}s")
    print(f"PAR-2:      {par2:.3f}s")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--cvc5",
        type=Path,
        default=ROOT / ".cache/cvc5-build/bin/cvc5",
    )
    result.add_argument(
        "--benchmarks",
        type=Path,
        default=ROOT / "benchmarks/smtlib-2025",
    )
    result.add_argument("--timeout", type=float, default=10.0)
    result.add_argument("--logic", action="append", default=[])
    result.add_argument("--limit", type=int)
    result.add_argument(
        "--workers",
        type=int,
        default=0,
        help="worker count exposed to submission.get_config; local runs use zero",
    )
    result.add_argument("--quiet", action="store_true")
    result.add_argument("--show-diagnostics", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    cvc5 = args.cvc5.resolve()
    benchmark_root = args.benchmarks.resolve()
    if not cvc5.is_file():
        raise SystemExit(f"cvc5 binary not found: {cvc5}; run `make build`")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.workers < 0:
        raise SystemExit("--workers cannot be negative")

    selected_logics = {logic.upper() for logic in args.logic}
    try:
        cases = load_cases(benchmark_root, selected_logics, args.limit)
        configs = {
            logic: load_config(
                next(case.formula for case in cases if case.logic == logic),
                args.workers,
            )
            for logic in {case.logic for case in cases}
        }
    except ValueError as error:
        raise SystemExit(f"submission_tests.py: {error}") from error

    print(f"cvc5:   {cvc5_version(cvc5)}")
    print(f"suite:  {benchmark_root} ({len(cases)} cases)")
    print(f"limit:  {args.timeout:g}s per case")
    runs: list[Run] = []
    for index, case in enumerate(cases, start=1):
        run = run_case(case, configs[case.logic], cvc5, args.timeout)
        runs.append(run)
        if not args.quiet:
            print(
                f"[{index:03d}/{len(cases):03d}] {outcome(run):7s} "
                f"{run.wall_seconds:7.3f}s  {case.logic:12s}  {case.relative}",
                flush=True,
            )
        if args.show_diagnostics and run.diagnostics:
            print(run.diagnostics.rstrip(), file=sys.stderr)
        if run.error:
            print(f"{case.relative}: {run.error}", file=sys.stderr)

    print_summary(runs, args.timeout)
    return 1 if any(run.wrong or run.error for run in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
