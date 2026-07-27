"""Load and validate the entrant-controlled solver configuration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import dataclasses
import importlib
from pathlib import Path
import re


LOGIC_RE = re.compile(
    rb"\(\s*set-logic\s+([A-Za-z0-9_]+)\s*\)",
    re.IGNORECASE,
)
MODES = frozenset({"sequential", "portfolio", "distributed"})
CONFIG_KEYS = frozenset(
    {"mode", "jobs_per_node", "local_replicas", "cvc5_args"}
)
RUNNER_MANAGED_ARGS = (
    "--lang",
    "--portfolio-jobs",
    "--tlimit",
    "--use-portfolio",
)


@dataclasses.dataclass(frozen=True)
class SolverConfig:
    mode: str
    jobs_per_node: int
    local_replicas: int
    cvc5_args: tuple[str, ...]


def read_logic(formula: Path) -> str:
    """Read the first SMT-LIB set-logic command, or return UNKNOWN."""
    with formula.open("rb") as handle:
        match = LOGIC_RE.search(handle.read(256 * 1024))
    return match.group(1).decode("ascii").upper() if match else "UNKNOWN"


def _positive_int(raw: object, name: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{name} must be an integer")
    if not 1 <= raw <= 256:
        raise ValueError(f"{name} must be between 1 and 256")
    return raw


def _cvc5_args(raw: object) -> tuple[str, ...]:
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("cvc5_args must be a list or tuple of strings")
    result: list[str] = []
    for argument in raw:
        if not isinstance(argument, str) or not argument.startswith("-"):
            raise ValueError("each cvc5 argument must be a non-empty option")
        if "\x00" in argument:
            raise ValueError("cvc5 arguments cannot contain NUL bytes")
        if argument.startswith(RUNNER_MANAGED_ARGS):
            raise ValueError(
                f"{argument!r} is managed by mode, jobs_per_node, or the scorer"
            )
        result.append(argument)
    return tuple(result)


def validate_config(raw: object) -> SolverConfig:
    """Validate the dictionary returned by ``submission.get_config``."""
    if not isinstance(raw, Mapping):
        raise ValueError("get_config must return a dictionary")
    unknown = set(raw) - CONFIG_KEYS
    missing = CONFIG_KEYS - set(raw)
    if unknown:
        raise ValueError(f"unknown configuration keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing configuration keys: {sorted(missing)}")

    mode = raw["mode"]
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    return SolverConfig(
        mode=mode,
        jobs_per_node=_positive_int(raw["jobs_per_node"], "jobs_per_node"),
        local_replicas=_positive_int(raw["local_replicas"], "local_replicas"),
        cvc5_args=_cvc5_args(raw["cvc5_args"]),
    )


def load_config(formula: Path, workers: int) -> SolverConfig:
    """Call the entrant's configuration function for one formula."""
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 0:
        raise ValueError("workers must be a non-negative integer")
    submission = importlib.import_module("submission")
    get_config = getattr(submission, "get_config", None)
    if not callable(get_config):
        raise ValueError("submission.py must define get_config(logic, workers)")
    return validate_config(get_config(read_logic(formula), workers))
