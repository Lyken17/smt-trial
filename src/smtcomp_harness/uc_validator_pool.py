from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import polars as pl
from smtcomp import archive, benchexec, defs, results, scoring, submission


RULES_URL = "https://smt-comp.github.io/2025/rules.pdf"
SOURCE_URL = "https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25"


def eligible_pairs(data: Path) -> list[tuple[defs.Division, str]]:
    """Return the maximal rules-compliant pool derivable from public 2025 data."""
    config = defs.Config(data)
    frame = results.helper_get_results(config, [], defs.Track.SingleQuery)
    frame = scoring.add_disagreements_info(frame, defs.Track.SingleQuery)
    uc_divisions = [int(division) for division in defs.tracks[defs.Track.UnsatCore]]
    rows = (
        frame.filter(pl.col("sound_solver"), pl.col("division").is_in(uc_divisions))
        .select("division", "solver")
        .unique()
        .sort("division", "solver")
        .collect()
        .iter_rows()
    )
    return [(defs.Division[defs.Division.name_of_int(division)], solver) for division, solver in rows]


def submissions_by_name(directory: Path):
    found = {}
    for path in sorted(directory.glob("*.json")):
        value = submission.read(str(path))
        if value.name in found:
            raise ValueError(f"duplicate official submission name: {value.name}")
        found[value.name] = (path, value)
    return found


def create_manifest(data: Path, submissions: Path, division: str | None) -> dict[str, object]:
    selected_division = None
    if division:
        if division not in defs.Division.__members__:
            raise ValueError(f"unknown Division: {division}")
        selected_division = defs.Division[division]
        if selected_division not in defs.tracks[defs.Track.UnsatCore]:
            raise ValueError(f"Division {division} is not in the UnsatCore Track")

    available = submissions_by_name(submissions)
    pairs = eligible_pairs(data)
    if selected_division is not None:
        pairs = [pair for pair in pairs if pair[0] == selected_division]
    missing = sorted({solver for _, solver in pairs if solver not in available})
    if missing:
        raise ValueError(f"official submission metadata missing for: {', '.join(missing)}")

    by_division: dict[str, list[dict[str, str]]] = {}
    for current_division, solver in pairs:
        path, _ = available[solver]
        by_division.setdefault(current_division.name, []).append(
            {"solver": solver, "submission": str(path.resolve())}
        )
    return {
        "schema": 1,
        "year": 2025,
        "track": "UnsatCoreValidation",
        "policy": "maximal-public-rules-compliant-pool",
        "exact_organizer_pool": False,
        "limitation": (
            "The rules say 'a selection' of sound Single Query solvers, but the organizers did not "
            "publish the final validator identity list. This manifest deterministically includes every "
            "public 2025 Single Query solver that is sound in each division."
        ),
        "rules_url": RULES_URL,
        "official_source_url": SOURCE_URL,
        "single_query_results": str((data / "results-sq-2025.json.gz").resolve()),
        "solver_count": len({solver for _, solver in pairs}),
        "solver_division_pair_count": len(pairs),
        "divisions": by_division,
    }


def write_manifest(value: dict[str, object], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + "\n")


def build_pool(data: Path, submissions: Path, cache: Path, manifest_path: Path, division: str | None) -> None:
    manifest = create_manifest(data, submissions, division)
    config = defs.Config(data)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "tools").mkdir(parents=True, exist_ok=True)
    properties = cache / "benchmarks" / "properties"
    properties.mkdir(parents=True, exist_ok=True)
    (properties / "SMT.prp").touch()
    run_definitions = cache / "run_definitions"
    run_definitions.mkdir(parents=True, exist_ok=True)

    loaded = submissions_by_name(submissions)
    xmls: list[dict[str, str]] = []
    solvers = sorted(
        {item["solver"] for items in manifest["divisions"].values() for item in items}  # type: ignore[union-attr]
    )
    for solver in solvers:
        _, value = loaded[solver]
        archive.download_unpack(value, cache)
        benchexec.generate_tool_modules(value, cache)

    for division_name, items in manifest["divisions"].items():  # type: ignore[union-attr]
        current_division = defs.Division[division_name]
        for item in items:
            solver = item["solver"]
            _, value = loaded[solver]
            tasks = benchexec.cmdtask_for_submission(
                value, cache, defs.Track.UnsatCoreValidation, current_division
            )
            if not tasks:
                raise ValueError(f"{solver} has no SingleQuery command for {division_name}")
            filename = benchexec.get_xml_name(value, defs.Track.UnsatCoreValidation, current_division)
            xml = run_definitions / filename
            benchexec.generate_unsatcore_validation_xml(
                config, tasks, xml, benchexec.tool_module_name(value, False)
            )
            xmls.append({"division": division_name, "solver": solver, "xml": str(xml.resolve())})
    manifest["run_definitions"] = xmls
    write_manifest(manifest, manifest_path)


def run_pool(cache: Path, manifest_path: Path, output: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    definitions = manifest.get("run_definitions")
    if not definitions:
        raise ValueError("manifest has no run_definitions; build the pool first")
    output = output.resolve()
    for item in definitions:
        destination = output / item["division"] / item["solver"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "benchexec.benchexec", item["xml"], "-o", str(destination)],
            cwd=cache,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the maximal public SMT-COMP 2025 UC validator pool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("manifest", "build"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--data", type=Path, required=True)
        sub.add_argument("--submissions", type=Path, required=True)
        sub.add_argument("--manifest", type=Path, required=True)
        sub.add_argument("--division")
        if name == "build":
            sub.add_argument("--cache", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "manifest":
        write_manifest(create_manifest(args.data, args.submissions, args.division), args.manifest)
    elif args.command == "build":
        build_pool(args.data, args.submissions, args.cache, args.manifest, args.division)
    else:
        run_pool(args.cache.resolve(), args.manifest, args.results)


if __name__ == "__main__":
    main()
