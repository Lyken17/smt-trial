from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from smtcomp import defs

from .config import args_for, load


LOGIC_RE = re.compile(rb"\(\s*set-logic\s+([^\s()]+)\s*\)", re.IGNORECASE)

PROTOCOL_ARGS = {
    "SingleQuery": ["-L", "smt2.6", "--no-incremental", "--no-type-checking", "--no-interactive"],
    "UnsatCore": ["-L", "smt2.6", "--no-incremental", "--no-type-checking", "--no-interactive"],
    "ModelValidation": ["-L", "smt2.6", "--no-incremental", "--no-type-checking", "--no-interactive"],
    "Parallel": ["-L", "smt2.6", "--no-incremental", "--no-type-checking", "--no-interactive"],
    "Incremental": [
        "-L",
        "smt2.6",
        "--incremental",
        "--print-success",
        "--no-type-checking",
        "--no-interactive",
    ],
}


def benchmark_logic(path: Path) -> str:
    with path.open("rb") as handle:
        match = LOGIC_RE.search(handle.read(1024 * 1024))
    if not match:
        raise ValueError(f"no set-logic in first MiB of {path}")
    return match.group(1).decode("ascii").upper()


def division_for(track_name: str, logic_name: str) -> str:
    track = defs.Track(track_name)
    logic = defs.Logic(logic_name)
    matches = [division for division, logics in defs.tracks[track].items() if logic in logics]
    if len(matches) != 1:
        raise ValueError(f"{logic_name} belongs to {len(matches)} divisions in {track_name}")
    return matches[0].name


def solver_args(config_path: Path, track_name: str, benchmark: Path) -> list[str]:
    config = load(config_path, track_name)
    logic = benchmark_logic(benchmark)
    division = division_for(track_name, logic)
    return [*PROTOCOL_ARGS[track_name], *args_for(config, division, logic)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cvc5", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("benchmark", type=Path)
    args = parser.parse_args()
    command = [
        str(args.cvc5.resolve()),
        *solver_args(args.config, args.track, args.benchmark),
        str(args.benchmark.resolve()),
    ]
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
