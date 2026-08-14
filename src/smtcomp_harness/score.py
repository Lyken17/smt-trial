from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile

import polars as pl


ALLOWED_KINDS = {
    "SingleQuery": {"par", "seq", "sat", "unsat", "24"},
    "Incremental": {"par"},
    "UnsatCore": {"par", "seq"},
    "ModelValidation": {"par", "seq"},
    "Parallel": {"par"},
}


def validate_score_coordinates(track_name: str, kind_name: str, division_name: str | None):
    from smtcomp import defs

    allowed = ALLOWED_KINDS.get(track_name)
    if allowed is None:
        raise ValueError(f"Track {track_name} has no regular SMT-COMP 2025 score")
    if kind_name not in allowed:
        raise ValueError(
            f"performance={kind_name} is not an official SMT-COMP 2025 score for {track_name}; "
            f"allowed: {', '.join(sorted(allowed))}"
        )
    if division_name is None:
        raise ValueError("Division is required; use `make score-matrix` to list legal combinations")
    if division_name not in defs.Division.__members__:
        raise ValueError(f"unknown Division: {division_name}")
    division = defs.Division[division_name]
    track = defs.Track(track_name)
    if division not in defs.tracks[track]:
        raise ValueError(f"Division {division_name} is not part of Track {track_name}")
    return track, division


def _result_sources(data: Path, sources: list[Path], stack: ExitStack) -> list[Path]:
    """Convert organizer JSON to the official parsed.feather input when needed."""
    from smtcomp import defs
    from smtcomp.unpack import read_cin

    if not any(path.name.endswith((".json", ".json.gz")) for path in sources):
        return sources
    benchmarks = defs.Benchmarks.model_validate_json(read_cin(data / "benchmarks-2025.json.gz"))
    files = [item.file for item in benchmarks.non_incremental] + [item.file for item in benchmarks.incremental]
    file_ids = {file: index for index, file in enumerate(files)}
    normalized: list[Path] = []
    for source in sources:
        if not source.name.endswith((".json", ".json.gz")):
            normalized.append(source)
            continue
        payload = defs.Results.model_validate_json(read_cin(source))
        rows = [
            {
                "solver": run.solver,
                "participation": 0,
                "track": int(run.track),
                "logic": int(run.file.logic),
                "file": file_ids[run.file],
                "answer": int(run.result),
                "cputime_s": run.cpu_time,
                "memory_B": run.memory_usage,
                "walltime_s": run.wallclock_time,
                "nb_answers": run.nb_answers,
                "benchmark_yml": "",
                "unsat_core": [],
            }
            for run in payload.results
        ]
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="smtcomp-result-")))
        pl.DataFrame(rows).write_ipc(directory / "parsed.feather")
        normalized.append(directory)
    return normalized


def _require_track_validation(track_name: str, sources: list[Path]) -> None:
    """Reject unvalidated local results; organizer JSON is already finalized."""
    from smtcomp import defs

    for source in sources:
        if source.name.endswith((".json", ".json.gz")):
            continue
        feather = source / "parsed.feather" if source.is_dir() else source
        if not feather.is_file():
            continue
        frame = pl.read_ipc(feather)
        if track_name == "ModelValidation" and (
            frame["answer"] == int(defs.Answer.ModelNotValidated)
        ).any():
            raise ValueError(f"ModelValidation results have not all been validated: {source}")
        if track_name == "UnsatCore":
            if "validation_attempted" not in frame.columns:
                raise ValueError(f"UnsatCore results do not contain validation evidence: {source}")
            pending = (frame["answer"] == int(defs.Answer.Unsat)) & ~frame["validation_attempted"]
            if pending.any():
                raise ValueError(f"UnsatCore results have unvalidated cores: {source}")


def score(data: Path, track_name: str, kind_name: str, sources: list[Path], division: str | None):
    # These imports intentionally come from the pinned upstream checkout
    # installed by scripts/bootstrap.sh. No scoring formula is reimplemented.
    from smtcomp import defs, results as official_results, scoring as official_scoring
    from smtcomp.utils import sort as official_sort

    track, division_id = validate_score_coordinates(track_name, kind_name, division)
    config = defs.Config(data)
    kind = official_scoring.Kind(kind_name)
    with ExitStack() as stack:
        _require_track_validation(track_name, sources)
        normalized = _result_sources(data, sources, stack)
        frame = official_results.helper_get_results(config, normalized, track)
        official_scoring.sanity_check(config, frame)
        frame = official_scoring.add_disagreements_info(frame, track).filter(disagreements=False).drop("disagreements")
        frame = official_scoring.benchmark_scoring(frame, track)
        frame = official_scoring.filter_for(kind, config, frame)
        by_division = official_scoring.division_score(frame)
        by_division = by_division.filter(pl.col("division") == int(division_id))
        by_division = official_sort(by_division, [("division", False)] + official_scoring.scores)
        detailed = by_division.collect().with_columns(
            division=pl.col("division").map_elements(defs.Division.name_of_int, return_dtype=pl.String)
        )
    total = detailed.group_by("solver").agg(
        pl.sum("error_score"),
        pl.sum("correctly_solved_score"),
        pl.sum("wallclock_time_score"),
        pl.sum("cpu_time_score"),
    )
    return detailed, total


def main() -> None:
    parser = argparse.ArgumentParser(description="Official SMT-COMP division scorer plus a non-official diagnostic sum")
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--kind", "--performance", dest="kind", choices=("par", "seq", "sat", "unsat", "24"), required=True)
    parser.add_argument("--division", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        validate_score_coordinates(args.track, args.kind, args.division)
    except ValueError as error:
        parser.error(str(error))
    detailed, total = score(args.data, args.track, args.kind, args.results, args.division)
    if args.json:
        print(json.dumps({"divisions": detailed.to_dicts(), "non_official_diagnostic_sum": total.to_dicts()}, indent=2))
    else:
        print("Official division scores")
        print(detailed)
        print("NON-OFFICIAL all-division diagnostic sum (not a ranking or award)")
        print(total)


if __name__ == "__main__":
    main()
