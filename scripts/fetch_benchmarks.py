#!/usr/bin/env python3
"""Fetch a small, deterministic SMT-LIB 2025 proxy benchmark set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGICS = (
    "ABVFP",
    "ALIA",
    "LIA",
    "NIA",
    "NRA",
    "QF_ALIA",
    "QF_AUFLIA",
    "QF_NIRA",
    "QF_S",
)
STATUS_RE = re.compile(
    rb"\(\s*set-info\s+:status\s+(sat|unsat|unknown)\s*\)",
    re.IGNORECASE,
)


def _read_versions() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (ROOT / "versions.env").read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _record_files(record: str) -> dict[str, dict[str, object]]:
    url = f"https://zenodo.org/api/records/{record}"
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    return {entry["key"]: entry for entry in data["files"]}


def _checksum(path: Path, algorithm: str = "md5") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(entry: dict[str, object], destination: Path) -> None:
    checksum_spec = str(entry["checksum"])
    algorithm, expected = checksum_spec.split(":", 1)
    if destination.is_file() and _checksum(destination, algorithm) == expected:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {entry['key']} ({entry['size']} bytes)")
    urllib.request.urlretrieve(str(entry["links"]["self"]), temporary)
    actual = _checksum(temporary, algorithm)
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"checksum mismatch for {entry['key']}: {actual} != {expected}"
        )
    temporary.replace(destination)


def _extract(archive: Path, destination: Path, checksum: str) -> None:
    marker = destination / ".archive-checksum"
    if marker.is_file() and marker.read_text().strip() == checksum:
        return
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    subprocess.run(
        ["tar", "--zstd", "-xf", str(archive), "-C", str(destination)],
        check=True,
    )
    marker.write_text(checksum + "\n")


def _status(path: Path) -> str | None:
    with path.open("rb") as handle:
        header = handle.read(256 * 1024)
    match = STATUS_RE.search(header)
    return match.group(1).decode().lower() if match else None


def _spread(paths: list[Path], count: int) -> list[Path]:
    if count <= 0:
        return []
    paths = sorted(paths, key=lambda path: (path.stat().st_size, str(path)))
    if len(paths) <= count:
        return paths
    if count == 1:
        return [paths[-1]]
    indices = {
        round(index * (len(paths) - 1) / (count - 1))
        for index in range(count)
    }
    return [paths[index] for index in sorted(indices)]


def _select(candidates: list[Path], count: int) -> list[tuple[Path, str]]:
    groups: dict[str, list[Path]] = {"sat": [], "unsat": []}
    for path in candidates:
        status = _status(path)
        if status in groups:
            groups[status].append(path)

    sat_target = count // 2
    unsat_target = count - sat_target
    selected: list[tuple[Path, str]] = []
    for status, target in (("sat", sat_target), ("unsat", unsat_target)):
        selected.extend((path, status) for path in _spread(groups[status], target))

    if len(selected) < count:
        used = {path for path, _ in selected}
        remaining = [
            (path, status)
            for status, paths in groups.items()
            for path in paths
            if path not in used
        ]
        remaining.sort(key=lambda item: (item[0].stat().st_size, str(item[0])))
        selected.extend(remaining[-(count - len(selected)) :])
    return sorted(selected, key=lambda item: (item[1], str(item[0])))


def _parser() -> argparse.ArgumentParser:
    versions = _read_versions()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record",
        default=versions["SMTLIB_2025_ZENODO_RECORD"],
        help="Zenodo record containing non-incremental SMT-LIB archives",
    )
    parser.add_argument(
        "--logic",
        action="append",
        dest="logics",
        help="logic archive to sample; repeatable",
    )
    parser.add_argument("--per-logic", type=int, default=12)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks/smtlib-2025",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.per_logic <= 0:
        raise SystemExit("--per-logic must be positive")
    logics = tuple(args.logics or DEFAULT_LOGICS)
    files = _record_files(str(args.record))
    archive_dir = ROOT / ".cache/smtlib-2025-archives"
    extract_root = ROOT / ".cache/smtlib-2025-extracted"
    args.output.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "zenodo_record": str(args.record),
        "selection": "status-balanced size quantiles",
        "per_logic": args.per_logic,
        "benchmarks": [],
    }
    output_entries: list[dict[str, object]] = []
    for logic in logics:
        key = f"{logic}.tar.zst"
        if key not in files:
            raise RuntimeError(f"Zenodo record {args.record} has no {key}")
        entry = files[key]
        archive = archive_dir / key
        _download(entry, archive)
        extracted = extract_root / logic
        _extract(archive, extracted, str(entry["checksum"]))
        candidates = sorted(extracted.rglob("*.smt2"))
        selected = _select(candidates, args.per_logic)
        logic_output = args.output / logic
        if logic_output.exists():
            shutil.rmtree(logic_output)
        logic_output.mkdir(parents=True)
        for source, status in selected:
            relative = source.relative_to(extracted)
            digest = hashlib.sha256(str(relative).encode()).hexdigest()[:10]
            destination = logic_output / f"{digest}-{source.name}"
            shutil.copy2(source, destination)
            output_entries.append(
                {
                    "logic": logic,
                    "status": status,
                    "source": str(relative),
                    "path": str(destination.relative_to(args.output)),
                    "size": source.stat().st_size,
                    "sha256": _checksum(source, "sha256"),
                }
            )
        print(f"{logic}: selected {len(selected)} / {len(candidates)}")

    manifest["benchmarks"] = output_entries
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"Wrote {len(output_entries)} benchmarks to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"fetch_benchmarks.py: {error}", file=sys.stderr)
        raise SystemExit(1)

