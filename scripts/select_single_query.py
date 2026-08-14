#!/usr/bin/env python3
"""Resume SMT-COMP's official Single Query selection and scrambling."""

from __future__ import annotations

import argparse
import concurrent.futures
from pathlib import Path

from rich.progress import track

from smtcomp import defs, scramble_benchmarks, selection


def output_paths(row: dict[str, object], destination: Path) -> tuple[Path, Path]:
    logic = str(defs.Logic.of_int(int(row["logic"])))
    directory = destination / logic
    scrambled = directory / scramble_benchmarks.scramble_basename(int(row["scramble_id"]))
    mangled = "_".join(
        (
            str(row["file"]),
            logic,
            str(row["family"]).replace("/", "__"),
            str(row["name"]),
        )
    )
    return scrambled, (directory / mangled).with_suffix(".yml")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--scrambler", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    config = defs.Config(args.data)
    selected = selection.helper(config, defs.Track.SingleQuery)
    selected = scramble_benchmarks.create_scramble_id(selected, config).filter(selected=True)
    frame = selected.select("scramble_id", "logic", "family", "name", "file").collect()

    destination = scramble_benchmarks.benchmark_files_dir(
        args.execution, defs.Track.SingleQuery
    )
    destination.mkdir(parents=True, exist_ok=True)
    frame.select("scramble_id", "file").write_csv(
        destination / scramble_benchmarks.csv_original_id_name
    )

    rows = frame.to_dicts()
    missing = [
        row
        for row in rows
        if not all(path.is_file() for path in output_paths(row, destination))
    ]
    print(
        f"Official Single Query selection: {len(rows)}; remaining: {len(missing)}",
        flush=True,
    )

    command = [
        args.scrambler,
        "-term_annot",
        "pattern",
        "-seed",
        str(config.seed),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                scramble_benchmarks.scramble_file,
                row,
                False,
                args.benchmarks,
                destination,
                command,
            )
            for row in missing
        ]
        for future in track(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            description="Scrambling missing official benchmarks...",
        ):
            future.result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
