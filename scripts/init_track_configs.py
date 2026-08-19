#!/usr/bin/env python3
"""Initialize missing Track/Performance tuning configurations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from smtcomp import defs

from smtcomp_harness.config import ALLOWED_PERFORMANCES


ROOT = Path(__file__).resolve().parents[1]
BASELINE_ARGS = ["--fp-exp", "--use-portfolio"]
TRACK_RESOURCES = {
    "SingleQuery": (4, 30 * 1024),
    "Incremental": (4, 30 * 1024),
    "UnsatCore": (4, 30 * 1024),
    "ModelValidation": (4, 30 * 1024),
    "Parallel": (128, 1000 * 1024),
}


def render_config(track_name: str, performance: str) -> str:
    track = defs.Track(track_name)
    cores, memory_mib = TRACK_RESOURCES[track_name]
    divisions = "\n".join(
        f"[division.{division.name}]\nargs = []"
        for division in sorted(defs.tracks[track], key=lambda item: item.name)
    )
    return f'''# Independent tuning candidate for {track_name}/{performance}.
# Rules: https://smt-comp.github.io/2025/rules.pdf
# Official scoring: https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py
[meta]
name = "cvc5-{track_name.lower()}-{performance}"
track = "{track_name}"
performance = "{performance}"
jobs = 1
cores = {cores}
memory_mib = {memory_mib}
wall_limit_s = 1200

[default]
args = {json.dumps(BASELINE_ARGS)}

{divisions}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", default="SingleQuery", choices=tuple(TRACK_RESOURCES))
    args = parser.parse_args()
    destination = ROOT / "configs" / "cvc5" / args.track
    created = 0
    for performance in sorted(ALLOWED_PERFORMANCES[args.track]):
        path = destination / f"{performance}.toml"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_config(args.track, performance))
        created += 1
    print(f"initialized {created} Track/Performance configs below {destination}")


if __name__ == "__main__":
    main()
