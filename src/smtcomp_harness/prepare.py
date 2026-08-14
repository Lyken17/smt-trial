from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

from smtcomp import defs

from .config import load


def prepare(
    track: str,
    config_path: Path,
    cvc5: Path,
    selection: Path,
    output: Path,
    division: str | None = None,
    trace_executor: Path | None = None,
) -> None:
    config_path = config_path.resolve()
    cvc5 = cvc5.resolve()
    selection = selection.resolve()
    if not cvc5.is_file() or not cvc5.stat().st_mode & 0o111:
        raise ValueError(f"cvc5 is missing or not executable: {cvc5}")
    validation = track == "UnsatCoreValidation"
    config_track = "SingleQuery" if validation else track
    pattern = "*.smt2" if validation else "*.yml"
    if not selection.is_dir() or not any(selection.glob(f"*/{pattern}")):
        raise ValueError(f"selected benchmark files are missing: {selection}")
    config = load(config_path, config_track)
    meta = config["meta"]
    if track == "Incremental":
        if trace_executor is None or not trace_executor.is_file() or not trace_executor.stat().st_mode & 0o111:
            raise ValueError("Incremental requires an executable official trace executor")
        tool = "smtcomp_harness.benchexec_tool_incremental"
    else:
        tool = "smtcomp_harness.benchexec_tool"
    if validation:
        cores = defs.Config.unsatcore_validation_cpuCores
        memory_mib = defs.Config.unsatcore_validation_memlimit_M
        wall_limit_s = defs.Config.unsatcore_validation_timelimit_s
    else:
        cores = meta["cores"]
        memory_mib = meta["memory_mib"]
        wall_limit_s = meta["wall_limit_s"]
    root = ET.Element(
        "benchmark",
        {
            "tool": tool,
            "timelimit": f"{wall_limit_s * cores}s",
            "walltimelimit": f"{wall_limit_s}s",
            "memlimit": f"{memory_mib} MB",
            "cpuCores": str(cores),
        },
    )
    run = ET.SubElement(root, "rundefinition", {"name": f"{meta['name']},0,{track}"})
    options = ["--config", str(config_path), "--cvc5", str(cvc5), "--track", config_track]
    if track == "Incremental":
        options.extend(("--trace-executor", str(trace_executor.resolve())))
    for value in options:
        ET.SubElement(run, "option").text = value
    tasks = ET.SubElement(run, "tasks", {"name": division or track})
    if division:
        mapping_track = defs.Track.UnsatCore if validation else defs.Track(track)
        if division not in defs.Division.__members__:
            raise ValueError(f"unknown Division: {division}")
        division_id = defs.Division[division]
        if division_id not in defs.tracks[mapping_track]:
            raise ValueError(f"Division {division} is not in Track {mapping_track}")
        for logic in sorted(defs.tracks[mapping_track][division_id], key=str):
            ET.SubElement(tasks, "include").text = str(selection / str(logic) / pattern)
    else:
        ET.SubElement(tasks, "include").text = str(selection / "*" / pattern)
    property_file = output.parent / "SMT.prp"
    property_file.parent.mkdir(parents=True, exist_ok=True)
    property_file.touch(exist_ok=True)
    ET.SubElement(root, "propertyfile").text = str(property_file.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate canonical SMT-COMP 2025 BenchExec XML")
    parser.add_argument(
        "--track",
        choices=("SingleQuery", "Incremental", "UnsatCore", "ModelValidation", "Parallel", "UnsatCoreValidation"),
        required=True,
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cvc5", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--division")
    parser.add_argument("--trace-executor", type=Path)
    args = parser.parse_args()
    prepare(
        args.track,
        args.config,
        args.cvc5,
        args.selection,
        args.output,
        args.division,
        args.trace_executor,
    )
    print(args.output)


if __name__ == "__main__":
    main()
