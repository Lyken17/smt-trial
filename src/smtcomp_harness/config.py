from __future__ import annotations

import argparse
import shlex
import tomllib
from pathlib import Path
from typing import Any


OWNED_FLAGS = (
    "-L",
    "--tlimit",
    "--rlimit",
    "--rlimit-per",
    "--segv-spin",
    "--lang",
    "--input-language",
    "--incremental",
    "--no-incremental",
    "--interactive",
    "--no-interactive",
    "--print-success",
    "--type-checking",
    "--no-type-checking",
)

EXPECTED = {
    "SingleQuery": {"cores": 4, "memory_mib": 30 * 1024, "wall_limit_s": 1200},
    "Incremental": {"cores": 4, "memory_mib": 30 * 1024, "wall_limit_s": 1200},
    "UnsatCore": {"cores": 4, "memory_mib": 30 * 1024, "wall_limit_s": 1200},
    "ModelValidation": {"cores": 4, "memory_mib": 30 * 1024, "wall_limit_s": 1200},
    "Parallel": {"cores": 128, "memory_mib": 1000 * 1024, "wall_limit_s": 1200},
}

ALLOWED_PERFORMANCES = {
    "SingleQuery": {"par", "seq", "sat", "unsat", "24"},
    "Incremental": {"par"},
    "UnsatCore": {"par", "seq"},
    "ModelValidation": {"par", "seq"},
    "Parallel": {"par"},
}


def load(path: Path, track: str | None = None) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data.get("meta"), dict) or not isinstance(data.get("default"), dict):
        raise ValueError("configuration needs [meta] and [default]")
    actual_track = str(data["meta"].get("track"))
    if track is not None and actual_track != track:
        raise ValueError(f"track mismatch: {actual_track!r} != {track!r}")
    if actual_track not in EXPECTED:
        raise ValueError(f"unsupported tuning track: {actual_track}")
    for key, value in EXPECTED[actual_track].items():
        if data["meta"].get(key) != value:
            raise ValueError(f"official {actual_track} {key} must be {value}")
    _validate_tree(data, actual_track)
    return data


def _validate_tree(data: dict[str, Any], track_name: str) -> None:
    from smtcomp import defs

    allowed_top = {"meta", "default", "division"}
    extra = set(data) - allowed_top
    if extra:
        raise ValueError(f"unsupported top-level keys: {sorted(extra)}")
    track = defs.Track(track_name)
    official_divisions = defs.tracks[track]
    performance = data["meta"].get("performance")
    if performance is not None:
        if performance not in ALLOWED_PERFORMANCES[track_name]:
            raise ValueError(f"performance {performance} is not valid for Track {track_name}")
        configured_divisions = set(data.get("division", {}))
        expected_divisions = {division.name for division in official_divisions}
        if configured_divisions != expected_divisions:
            raise ValueError("a Track/Performance config must contain every official Division")
    for division_name, division_section in data.get("division", {}).items():
        if division_name not in defs.Division.__members__:
            raise ValueError(f"unknown Division in {track_name}: {division_name}")
        division = defs.Division[division_name]
        if division not in official_divisions:
            raise ValueError(f"Division {division_name} is not in Track {track_name}")
        official_logics = official_divisions[division]
        for logic_name in division_section.get("logic", {}):
            if logic_name not in defs.Logic.__members__:
                raise ValueError(f"unknown Logic in {division_name}: {logic_name}")
            if defs.Logic[logic_name] not in official_logics:
                raise ValueError(f"Logic {logic_name} is not in {track_name}/{division_name}")

    for section_name, section in _sections(data):
        extra_keys = set(section) - {"args", "logic"}
        if extra_keys:
            raise ValueError(f"{section_name}: unsupported keys {sorted(extra_keys)}")
        args = section.get("args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ValueError(f"{section_name}.args must be an array of strings")
        for arg in args:
            if any(arg == flag or arg.startswith(flag + "=") for flag in OWNED_FLAGS):
                raise ValueError(f"{section_name}: harness-owned option is forbidden: {arg}")


def _sections(data: dict[str, Any]):
    yield "default", data["default"]
    for division, section in data.get("division", {}).items():
        yield f"division.{division}", section
        for logic, logic_section in section.get("logic", {}).items():
            yield f"division.{division}.logic.{logic}", logic_section


def args_for(data: dict[str, Any], division: str, logic: str) -> list[str]:
    result = list(data["default"].get("args", []))
    section = data.get("division", {}).get(division, {})
    result.extend(section.get("args", []))
    result.extend(section.get("logic", {}).get(logic, {}).get("args", []))
    return result


def validate_performance_request(data: dict[str, Any], performance: str | None) -> None:
    expected_performance = data["meta"].get("performance")
    if expected_performance is None:
        return
    if performance != expected_performance:
        raise ValueError(
            f"config is for performance {expected_performance}, requested {performance}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--track")
    parser.add_argument("--division")
    parser.add_argument("--logic")
    ns = parser.parse_args()
    data = load(ns.config, ns.track)
    if ns.division and ns.logic:
        print(shlex.join(args_for(data, ns.division, ns.logic)))
    else:
        print(f"valid: {data['meta']['name']} ({data['meta']['track']})")


if __name__ == "__main__":
    main()
