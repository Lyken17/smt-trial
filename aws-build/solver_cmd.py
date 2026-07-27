"""SMT-COMP 2026 AWS harness adapter for cvc5-cloud."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from common.solver_io import SolverInput, SolverResultCode


CVC5 = "/opt/cvc5/bin/cvc5"
RUNNER = "/opt/cvc5-cloud/cvc5_cloud/runner.py"
DEFAULT_JOBS_PER_NODE = 8


def _default_mode(s_input: SolverInput) -> str:
    solver_name = os.environ.get("SOLVER_NAME", "")
    if s_input.worker_node_ips or solver_name.endswith("-cloud"):
        return "distributed"
    if solver_name.endswith("-sequential"):
        return "sequential"
    return "portfolio"


def get_run_command(s_input: SolverInput) -> List[str]:
    """Map a harness input to the cloud launcher command."""
    command = [
        "/usr/bin/python3",
        RUNNER,
        "--cvc5",
        CVC5,
        "--mode",
        _default_mode(s_input),
        "--timeout-seconds",
        str(s_input.timeout_seconds),
        "--jobs-per-node",
        str(DEFAULT_JOBS_PER_NODE),
    ]
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

