#!/usr/bin/env python3
"""Resume official SMT-COMP selection and scrambling for regular tracks."""

from __future__ import annotations

import argparse
import concurrent.futures
from pathlib import Path

from rich.progress import track as progress

from smtcomp import defs, scramble_benchmarks, selection


SUPPORTED = (
    defs.Track.SingleQuery,
    defs.Track.Incremental,
    defs.Track.UnsatCore,
    defs.Track.ModelValidation,
)


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


def scramble_command(track: defs.Track, scrambler: Path, seed: int) -> tuple[list[object], bool]:
    command: list[object] = [scrambler, "-term_annot", "pattern"]
    incremental = track == defs.Track.Incremental
    if incremental:
        command.extend(("-incremental", "true"))
    elif track == defs.Track.ModelValidation:
        command.extend(("-gen-model-val", "true"))
    elif track == defs.Track.UnsatCore:
        command.extend(("-gen-unsat-core", "true"))
    command.extend(("-seed", str(seed)))
    return command, incremental


def repair_task_yaml(
    row: dict[str, object],
    track: defs.Track,
    benchmarks: Path,
    destination: Path,
) -> bool:
    """Generate only the official YAML when its non-empty scrambled input exists."""
    scrambled, task = output_paths(row, destination)
    if not scrambled.is_file() or scrambled.stat().st_size == 0:
        return False
    if task.is_file() and task.stat().st_size > 0:
        return True
    source_kind = "incremental" if track == defs.Track.Incremental else "non-incremental"
    original = (
        benchmarks
        / source_kind
        / str(defs.Logic.of_int(int(row["logic"])))
        / str(row["family"])
        / str(row["name"])
    )
    expected = None
    if track != defs.Track.Incremental:
        # Same official status regex/semantics as get_expected_result, streamed
        # so repairing a YAML does not load a multi-gigabyte benchmark in RAM.
        with original.open(errors="replace") as handle:
            for line in handle:
                match = scramble_benchmarks.status_pattern.search(line)
                if match and match.group(2) != "unknown":
                    expected = match.group(2) == "sat"
                    break
    scramble_benchmarks.generate_benchmark_yml(
        task,
        scrambled,
        expected,
        original.relative_to(benchmarks),
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", required=True, choices=tuple(str(item) for item in SUPPORTED))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--scrambler", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    competition_track = defs.Track(args.track)
    config = defs.Config(args.data)
    selected = selection.helper(config, competition_track)
    selected = scramble_benchmarks.create_scramble_id(selected, config).filter(selected=True)
    frame = selected.select("scramble_id", "logic", "family", "name", "file").collect()
    destination = scramble_benchmarks.benchmark_files_dir(args.execution, competition_track)
    destination.mkdir(parents=True, exist_ok=True)
    # Resolve cache symlinks once. Re-resolving a WSL workspace symlink for
    # every one of 100k+ files makes resume checks needlessly slow.
    destination = destination.resolve()
    frame.select("scramble_id", "file").write_csv(
        destination / scramble_benchmarks.csv_original_id_name
    )

    rows = frame.to_dicts()
    repaired = 0
    missing = []
    for row in rows:
        scrambled, task = output_paths(row, destination)
        if repair_task_yaml(row, competition_track, args.benchmarks, destination):
            repaired += 1
            continue
        if not (
            scrambled.is_file()
            and scrambled.stat().st_size > 0
            and task.is_file()
            and task.stat().st_size > 0
        ):
            missing.append(row)
    print(
        f"Official {competition_track} selection: {len(rows)}; remaining: {len(missing)}; "
        f"ready/repaired: {repaired}",
        flush=True,
    )

    command, incremental = scramble_command(competition_track, args.scrambler, config.seed)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                scramble_benchmarks.scramble_file,
                row,
                incremental,
                args.benchmarks,
                destination,
                command,
            )
            for row in missing
        ]
        for future in progress(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            description=f"Scrambling missing {competition_track} benchmarks...",
        ):
            future.result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
