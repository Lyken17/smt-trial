#!/usr/bin/env python3
"""Initialize missing Track/Performance tuning configurations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from smtcomp import defs

from smtcomp_harness.config import ALLOWED_PERFORMANCES


ROOT = Path(__file__).resolve().parents[1]
BASELINE_ARGS = ["--quiet", "--fp-exp", "--use-portfolio"]


def render_single_query(performance: str) -> str:
    divisions = "\n".join(
        f"[division.{division.name}]\nargs = []"
        for division in sorted(defs.tracks[defs.Track.SingleQuery], key=lambda item: item.name)
    )
    return f'''# Independent tuning candidate for SingleQuery/{performance}.
# Rules: https://smt-comp.github.io/2025/rules.pdf
# Official scoring: https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py
[meta]
name = "cvc5-single-query-{performance}"
track = "SingleQuery"
performance = "{performance}"
jobs = 1
cores = 4
memory_mib = 30720
wall_limit_s = 1200

[default]
args = {json.dumps(BASELINE_ARGS)}

{divisions}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", default="SingleQuery", choices=("SingleQuery",))
    args = parser.parse_args()
    destination = ROOT / "configs" / "cvc5" / args.track
    created = 0
    for performance in sorted(ALLOWED_PERFORMANCES[args.track]):
        path = destination / f"{performance}.toml"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_single_query(performance))
        created += 1
    print(f"initialized {created} Track/Performance configs below {destination}")


if __name__ == "__main__":
    main()
