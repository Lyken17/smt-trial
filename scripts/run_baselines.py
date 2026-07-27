#!/usr/bin/env python3
"""Run reproducible sequential and portfolio cvc5 baselines."""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cvc5_cloud.runner import Mode, RaceConfig, Result, run_race


STATUS_RE = re.compile(
    rb"\(\s*set-info\s+:status\s+(sat|unsat)\s*\)",
    re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True)
class Baseline:
    name: str
    mode: Mode
    jobs_per_node: int
    local_replicas: int


def expected_status(path: Path) -> str | None:
    with path.open("rb") as handle:
        match = STATUS_RE.search(handle.read(256 * 1024))
    return match.group(1).decode().lower() if match else None


def cvc5_version(binary: Path) -> str:
    completed = subprocess.run(
        [str(binary), "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.stdout.strip().splitlines()[0]


def run_one(
    baseline: Baseline,
    cvc5: Path,
    formula: Path,
    timeout: float,
) -> tuple[Result, float, str | None]:
    started = time.perf_counter()
    error: str | None = None
    try:
        result = run_race(
            RaceConfig(
                cvc5=cvc5,
                formula=formula,
                timeout_seconds=timeout,
                mode=baseline.mode,
                jobs_per_node=baseline.jobs_per_node,
                local_replicas=baseline.local_replicas,
                shutdown_grace_seconds=min(0.5, timeout / 10),
            )
        )
    except Exception as exception:
        result = Result.UNKNOWN
        error = f"{type(exception).__name__}: {exception}"
    elapsed = min(time.perf_counter() - started, timeout)
    return result, elapsed, error


def summarize(
    rows: list[dict[str, object]],
    baselines: list[Baseline],
    timeout: float,
) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for baseline in baselines:
        selected = [row for row in rows if row["baseline"] == baseline.name]
        correct = sum(row["correct"] is True for row in selected)
        wrong = sum(
            row["result"] in ("sat", "unsat") and row["correct"] is False
            for row in selected
        )
        unknown = sum(row["result"] == "unknown" for row in selected)
        errors = sum(bool(row["error"]) for row in selected)
        total_time = sum(float(row["wall_seconds"]) for row in selected)
        par2 = sum(
            float(row["wall_seconds"]) if row["correct"] else 2 * timeout
            for row in selected
        )
        summary.append(
            {
                "baseline": baseline.name,
                "benchmarks": len(selected),
                "correct": correct,
                "wrong": wrong,
                "unknown": unknown,
                "errors": errors,
                "total_wall_seconds": round(total_time, 6),
                "par2_seconds": round(par2, 6),
            }
        )
    return summary


def markdown_report(
    metadata: dict[str, object],
    summary: list[dict[str, object]],
) -> str:
    lines = [
        "# Baseline Results",
        "",
        f"- cvc5: `{metadata['cvc5_version']}`",
        f"- host: `{metadata['host']}`",
        f"- timeout: `{metadata['timeout_seconds']}s` per benchmark",
        f"- benchmark root: `{metadata['benchmark_root']}`",
        "",
        "| Baseline | Correct | Wrong | Unknown | Errors | Total wall (s) | PAR-2 (s) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['baseline']} | {row['correct']}/{row['benchmarks']} | "
            f"{row['wrong']} | {row['unknown']} | {row['errors']} | "
            f"{row['total_wall_seconds']:.3f} | {row['par2_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The seeded race is a single-host emulation of the distributed design. "
            "It validates orchestration but is not an AWS scaling measurement.",
            "",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cvc5", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    cvc5 = args.cvc5.resolve()
    benchmark_root = args.benchmarks.resolve()
    if not cvc5.is_file():
        raise SystemExit(f"cvc5 binary not found: {cvc5}")
    if args.timeout <= 0 or args.jobs <= 0:
        raise SystemExit("--timeout and --jobs must be positive")

    formulas = [
        path
        for path in sorted(benchmark_root.rglob("*.smt2"))
        if expected_status(path) in ("sat", "unsat")
    ]
    if args.limit is not None:
        formulas = formulas[: args.limit]
    if not formulas:
        raise SystemExit(f"no labeled .smt2 benchmarks under {benchmark_root}")

    race_replicas = min(4, args.jobs)
    race_jobs = max(1, args.jobs // race_replicas)
    baselines = [
        Baseline("sequential", Mode.SEQUENTIAL, 1, 1),
        Baseline(f"portfolio-{args.jobs}", Mode.PORTFOLIO, args.jobs, 1),
        Baseline(
            f"seeded-race-{race_replicas}x{race_jobs}",
            Mode.DISTRIBUTED,
            race_jobs,
            race_replicas,
        ),
    ]

    rows: list[dict[str, object]] = []
    for formula in formulas:
        expected = expected_status(formula)
        assert expected is not None
        for baseline in baselines:
            relative = formula.relative_to(benchmark_root)
            print(f"{baseline.name:22s} {relative}")
            result, elapsed, error = run_one(
                baseline,
                cvc5,
                formula,
                args.timeout,
            )
            rows.append(
                {
                    "baseline": baseline.name,
                    "benchmark": str(relative),
                    "expected": expected,
                    "result": result.value,
                    "correct": result.value == expected,
                    "wall_seconds": round(elapsed, 6),
                    "error": error or "",
                }
            )

    summary = summarize(rows, baselines, args.timeout)
    metadata: dict[str, object] = {
        "cvc5": str(cvc5),
        "cvc5_version": cvc5_version(cvc5),
        "host": platform.node(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "timeout_seconds": args.timeout,
        "jobs": args.jobs,
        "benchmark_root": str(benchmark_root),
        "benchmark_count": len(formulas),
    }

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "summary.json").write_text(
        json.dumps(
            {"metadata": metadata, "baselines": summary},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    report = markdown_report(metadata, summary)
    (args.output / "REPORT.md").write_text(report)
    print()
    print(report)
    return 1 if any(row["wrong"] for row in summary) else 0


if __name__ == "__main__":
    raise SystemExit(main())

