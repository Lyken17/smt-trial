#!/usr/bin/env python3
"""Audit an SMT-COMP 2025 selected benchmark directory for completeness."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re


EXPECTED = {
    "SingleQuery": ("files", 129361),
    "Incremental": ("files_inc", 22942),
    "UnsatCore": ("files_unsatcore", 70604),
    "ModelValidation": ("files_model", 59762),
    "Parallel": ("files_parallel", 400),
}
INPUT_FILE = re.compile(r"^input_files:\s*['\"]?([^'\"\s]+)", re.MULTILINE)


def audit(track: str, execution: Path) -> None:
    directory_name, expected = EXPECTED[track]
    root = (execution / "benchmarks" / directory_name).resolve()
    if not root.is_dir():
        raise ValueError(f"selection directory is missing: {root}")

    ymls = list(root.glob("*/*.yml"))
    smt2s = list(root.glob("*/*.smt2"))
    mapping = root / "original_id.csv"
    if not mapping.is_file():
        raise ValueError(f"official original-id mapping is missing: {mapping}")
    with mapping.open(newline="") as handle:
        mapping_rows = sum(1 for _ in csv.DictReader(handle))

    failures: list[str] = []
    for label, actual in (("YAML tasks", len(ymls)), ("SMT2 files", len(smt2s)), ("mapping rows", mapping_rows)):
        if actual != expected:
            failures.append(f"{label}: expected {expected}, found {actual}")
    nonempty_inputs = {path for path in smt2s if path.stat().st_size > 0}
    empty = [path for path in smt2s if path not in nonempty_inputs]
    if empty:
        failures.append(f"empty SMT2 files: {len(empty)} (first: {empty[0]})")

    broken = []
    referenced: set[Path] = set()
    for task in ymls:
        match = INPUT_FILE.search(task.read_text(errors="replace"))
        if match is None:
            broken.append(f"{task}: no input_files")
            continue
        benchmark = task.parent / match.group(1)
        referenced.add(benchmark)
        if benchmark not in nonempty_inputs:
            broken.append(f"{task}: missing/empty {benchmark.name}")
    if broken:
        failures.append(f"broken YAML tasks: {len(broken)} (first: {broken[0]})")
    if len(referenced) != expected:
        failures.append(f"unique YAML inputs: expected {expected}, found {len(referenced)}")

    if failures:
        raise ValueError(f"{track} selection is incomplete:\n  " + "\n  ".join(failures))
    print(f"{track}: complete official selection ({expected} YAML + {expected} non-empty SMT2)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track", choices=tuple(EXPECTED) + ("all",))
    parser.add_argument("--execution", type=Path, default=Path(".cache/execution"))
    args = parser.parse_args()
    tracks = EXPECTED if args.track == "all" else (args.track,)
    for track in tracks:
        audit(track, args.execution)


if __name__ == "__main__":
    main()
