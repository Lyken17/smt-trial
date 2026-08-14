from __future__ import annotations

import argparse
import json

from smtcomp import defs

from .score import ALLOWED_KINDS


PERFORMANCE_ORDER = ("par", "seq", "24", "sat", "unsat")


def combinations() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for track_name, kinds in ALLOWED_KINDS.items():
        track = defs.Track(track_name)
        for division in sorted(defs.tracks[track], key=str):
            for performance in PERFORMANCE_ORDER:
                if performance in kinds:
                    rows.append(
                        {
                            "track": track_name,
                            "division": division.name,
                            "performance": performance,
                        }
                    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="List every legal SMT-COMP 2025 score coordinate")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = combinations()
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    print("TRACK\tDIVISION\tPERFORMANCE")
    for row in rows:
        print(f"{row['track']}\t{row['division']}\t{row['performance']}")


if __name__ == "__main__":
    main()
