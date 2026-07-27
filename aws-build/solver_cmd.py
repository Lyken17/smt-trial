"""SMT-COMP AWS harness adapter for the configured cvc5 entry."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import List

from common.solver_io import SolverInput, SolverResultCode


CVC5 = "/opt/cvc5/bin/cvc5"
APP_ROOT = Path("/opt/cvc5-cloud")
RUNNER = APP_ROOT / "cvc5_cloud/runner.py"
if APP_ROOT.is_dir():
    sys.path.insert(0, str(APP_ROOT))

from cvc5_cloud.configuration import load_config



def get_run_command(s_input: SolverInput) -> List[str]:
    """Map a harness input to the cloud launcher command."""
    config = load_config(
        Path(s_input.formula_file),
        workers=len(s_input.worker_node_ips),
    )
    command = [
        "/usr/bin/python3",
        str(RUNNER),
        "--cvc5",
        CVC5,
        "--mode",
        config.mode,
        "--timeout-seconds",
        str(s_input.timeout_seconds),
        "--jobs-per-node",
        str(config.jobs_per_node),
        "--local-replicas",
        str(config.local_replicas),
    ]
    command.extend(f"--cvc5-arg={argument}" for argument in config.cvc5_args)
    for host in s_input.worker_node_ips:
        command.extend(("--host", host))
    command.extend(s_input.solver_argument_list)
    command.append(str(s_input.formula_file))
    return command


def get_solver_result(stdout_path: Path) -> SolverResultCode:
    """Read the last exact result emitted by the launcher."""
    if not stdout_path.exists():
        return SolverResultCode.INDETERMINATE
    lines = stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        normalized = line.strip().lower()
        if normalized in ("sat", "s satisfiable"):
            return SolverResultCode.SAT
        if normalized in ("unsat", "s unsatisfiable"):
            return SolverResultCode.UNSAT
        if normalized in ("unknown", "s unknown", "c unknown"):
            return SolverResultCode.UNKNOWN
    return SolverResultCode.INDETERMINATE


def get_cleanup_command() -> List[str]:
    """Stop residual remote cvc5 processes and remove staged formulas."""
    script = (
        "pkill -TERM -x cvc5 2>/dev/null || true; "
        "sleep 0.2; "
        "pkill -KILL -x cvc5 2>/dev/null || true; "
        "find /tmp -maxdepth 1 -type f -name 'cvc5-cloud-*.smt2' "
        "-delete 2>/dev/null || true; "
        "exit 0"
    )
    return ["bash", "-c", script]
