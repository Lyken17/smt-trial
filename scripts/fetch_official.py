#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"


def versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in (ROOT / "versions.env").read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value
    return result


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def curl_download(url: str, target: Path, byte_range: tuple[int, int] | None = None) -> None:
    command = [
        "curl", "--fail", "--location", "--retry", "8", "--retry-all-errors",
        "--connect-timeout", "60", "--speed-time", "30", "--speed-limit", "1024",
    ]
    if byte_range is not None:
        command.extend(["--range", f"{byte_range[0]}-{byte_range[1]}"])
    command.extend(["--output", str(target), "--silent", "--show-error", url])
    subprocess.run(command, check=True)


def segmented_download(url: str, partial: Path, size: int, segments: int) -> None:
    segment_size = (size + segments - 1) // segments
    ranges = [
        (index, start, min(size - 1, start + segment_size - 1))
        for index in range(segments)
        if (start := index * segment_size) < size
    ]
    has_complete_segment = any(
        Path(f"{partial}.{index:03d}").is_file()
        and Path(f"{partial}.{index:03d}").stat().st_size == end - start + 1
        for index, start, end in ranges
    )

    def fetch_range(item: tuple[int, int, int]) -> Path:
        index, start, end = item
        segment = Path(f"{partial}.{index:03d}")
        expected_size = end - start + 1
        # Temporary format used before subchunks were introduced.
        Path(f"{segment}.chunk").unlink(missing_ok=True)
        if segment.is_file() and segment.stat().st_size > expected_size:
            segment.unlink(missing_ok=True)
        current_size = segment.stat().st_size if segment.is_file() else 0
        if current_size == expected_size:
            return segment

        chunk_size = 16 * 1024 * 1024
        chunks = [
            (chunk_index, chunk_start, min(end, chunk_start + chunk_size - 1))
            for chunk_index, chunk_start in enumerate(range(start + current_size, end + 1, chunk_size))
        ]

        def fetch_chunk(chunk_item: tuple[int, int, int]) -> Path:
            chunk_index, chunk_start, chunk_end = chunk_item
            chunk = Path(f"{segment}.chunk.{chunk_index:03d}")
            wanted = chunk_end - chunk_start + 1
            if chunk.is_file() and chunk.stat().st_size > wanted:
                chunk.unlink()
            for _ in range(16):
                have = chunk.stat().st_size if chunk.is_file() else 0
                if have == wanted:
                    return chunk
                next_part = Path(f"{chunk}.next")
                next_part.unlink(missing_ok=True)
                try:
                    curl_download(url, next_part, (chunk_start + have, chunk_end))
                except subprocess.CalledProcessError:
                    pass
                received = next_part.stat().st_size if next_part.is_file() else 0
                if received > wanted - have:
                    next_part.unlink(missing_ok=True)
                    raise RuntimeError(f"invalid byte range {chunk_start}-{chunk_end} for {url}")
                if received:
                    with chunk.open("ab") as output, next_part.open("rb") as source:
                        shutil.copyfileobj(source, output, 1024 * 1024)
                    next_part.unlink()
            raise RuntimeError(f"failed byte range {chunk_start}-{chunk_end} for {url}")

        chunk_jobs = min(4 if has_complete_segment else 1, len(chunks))
        with concurrent.futures.ThreadPoolExecutor(max_workers=chunk_jobs) as executor:
            parts = list(executor.map(fetch_chunk, chunks))
        with segment.open("ab") as output:
            for chunk in parts:
                with chunk.open("rb") as source:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                chunk.unlink()
        if segment.stat().st_size != expected_size:
            raise RuntimeError(f"invalid assembled byte range {start}-{end} for {url}")
        return segment

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ranges)) as executor:
        parts = list(executor.map(fetch_range, ranges))
    partial.unlink(missing_ok=True)
    with partial.open("wb") as output:
        for part in parts:
            with part.open("rb") as source:
                shutil.copyfileobj(source, output, 1024 * 1024)
    if partial.stat().st_size != size:
        raise RuntimeError(f"invalid assembled size for {url}")


def download(
    url: str, target: Path, checksum: str | None = None, size: int | None = None
) -> None:
    if checksum is None and target.is_file():
        return
    if checksum:
        algorithm, expected = checksum.split(":", 1) if ":" in checksum else ("sha256", checksum)
        if target.is_file() and digest(target, algorithm) == expected:
            return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    print(f"download {url}")
    for integrity_attempt in range(1, 5):
        partial.unlink(missing_ok=True)
        segments = max(1, int(os.environ.get("DOWNLOAD_SEGMENTS", "1")))
        if size is not None and size >= 1024 * 1024 and segments > 1:
            segmented_download(url, partial, size, segments)
        else:
            curl_download(url, partial)
        if checksum is None or digest(partial, algorithm) == expected:
            partial.replace(target)
            for artifact in partial.parent.glob(partial.name + ".*"):
                artifact.unlink()
            return
        partial.unlink(missing_ok=True)
        for artifact in partial.parent.glob(partial.name + ".*"):
            artifact.unlink()
        print(f"checksum mismatch, retry {integrity_attempt}/4: {url}", file=sys.stderr)
    raise RuntimeError(f"checksum mismatch after 4 downloads for {url}")


def github_tree(revision: str) -> list[str]:
    url = f"https://api.github.com/repos/SMT-COMP/smt-comp.github.io/git/trees/{revision}?recursive=1"
    request = CACHE / "downloads" / f"smtcomp-tree-{revision}.json"
    download(url, request)
    payload = json.loads(request.read_text())
    if payload.get("truncated"):
        raise RuntimeError("GitHub returned a truncated official repository tree")
    return [item["path"] for item in payload["tree"] if item["type"] == "blob"]


def fetch_metadata(v: dict[str, str]) -> None:
    revision = v["SMTCOMP_REV"]
    base = f"https://raw.githubusercontent.com/SMT-COMP/smt-comp.github.io/{revision}"
    paths = github_tree(revision)
    wanted = [
        path
        for path in paths
        if (
            path == "data/benchmarks-2025.json.gz"
            or path.startswith("data/results-sq-20") and path.endswith(".json.gz")
            or path.startswith("data/results-inc-2025")
            or path.startswith("data/results-uc-2025")
            or path.startswith("data/results-mv-2025")
            or path.startswith("data/results-parallel-2025")
            or path.startswith("submissions/") and path.endswith(".json") and "/template/" not in path
        )
    ]
    official = CACHE / "official"
    for path in wanted:
        download(f"{base}/{path}", official / path)
    manifest = {
        "source": v["SMTCOMP_REPOSITORY"],
        "revision": revision,
        "files": sorted(wanted),
    }
    (official / "SOURCE.json").write_text(json.dumps(manifest, indent=2) + "\n")


def safe_extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"unsafe ZIP member: {member.filename}")
        source.extractall(destination)


def fetch_solver(v: dict[str, str], wanted: set[str] | None = None) -> None:
    for label, url_key, hash_key in (
        ("default", "CVC5_ARCHIVE_URL", "CVC5_ARCHIVE_SHA256"),
        ("incremental", "CVC5_INCREMENTAL_URL", "CVC5_INCREMENTAL_SHA256"),
    ):
        if wanted is not None and label not in wanted:
            continue
        archive = CACHE / "downloads" / f"cvc5-{label}.zip"
        download(v[url_key], archive, v[hash_key])
        destination = CACHE / "solver" / label
        marker = destination / ".sha256"
        if marker.is_file() and marker.read_text().strip() == v[hash_key]:
            continue
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True)
        safe_extract_zip(archive, destination)
        marker.write_text(v[hash_key] + "\n")


def record_files(record: str) -> list[dict[str, object]]:
    request = CACHE / "downloads" / f"zenodo-{record}.json"
    download(f"https://zenodo.org/api/records/{record}", request)
    payload = json.loads(request.read_text())
    return payload["files"]


def safe_tar_members(archive: Path) -> list[str]:
    result = subprocess.run(
        ["tar", "--zstd", "-tf", str(archive)], check=True, text=True, capture_output=True
    )
    members = [line for line in result.stdout.splitlines() if line]
    for member in members:
        path = PurePosixPath(member)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"unsafe tar member: {member}")
    return members


def fetch_benchmark_release(record: str, kind: str) -> None:
    destination = CACHE / "benchmarks"
    marker_directory = destination / kind
    marker_directory.mkdir(parents=True, exist_ok=True)
    entries = [entry for entry in record_files(record) if str(entry["key"]).endswith(".tar.zst")]

    def fetch_entry(entry: dict[str, object]) -> None:
        key = str(entry["key"])
        archive = CACHE / "downloads" / f"zenodo-{record}" / key
        download(
            str(entry["links"]["self"]), archive, str(entry["checksum"]), int(entry["size"])
        )

    jobs = max(1, int(os.environ.get("DOWNLOAD_JOBS", "8")))
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        list(executor.map(fetch_entry, entries))

    def extract_entry(entry: dict[str, object]) -> None:
        key = str(entry["key"])
        archive = CACHE / "downloads" / f"zenodo-{record}" / key
        marker = marker_directory / f".{key}.checksum"
        if marker.is_file() and marker.read_text().strip() == str(entry["checksum"]):
            return
        safe_tar_members(archive)
        extract_destination = destination
        large_logic = os.environ.get("LARGE_LOGIC")
        logic_path = destination / kind / str(large_logic)
        if large_logic and logic_path.is_symlink() and key == f"{large_logic}.tar.zst":
            configured = logic_path.resolve()
            expected_tail = Path(kind) / large_logic
            if Path(*configured.parts[-2:]) != expected_tail:
                raise RuntimeError(
                    f"large-logic cache must end in {expected_tail}: {configured}"
                )
            # The archive contains kind/logic/... paths. Extracting directly at
            # this root avoids GNU tar attempting cross-filesystem renames
            # through the workspace symlink.
            extract_destination = configured.parents[1]
            extract_destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "tar",
                "--zstd",
                "--keep-directory-symlink",
                "-xf",
                str(archive),
                "-C",
                str(extract_destination),
            ],
            check=True,
        )
        marker.write_text(str(entry["checksum"]) + "\n")

    extract_jobs = max(1, int(os.environ.get("EXTRACT_JOBS", "12")))
    with concurrent.futures.ThreadPoolExecutor(max_workers=extract_jobs) as executor:
        list(executor.map(extract_entry, entries))


def fetch_benchmarks(v: dict[str, str]) -> None:
    fetch_benchmark_release(v["SMTLIB_NON_INCREMENTAL_RECORD"], "non-incremental")
    fetch_benchmark_release(v["SMTLIB_INCREMENTAL_RECORD"], "incremental")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "component",
        choices=(
            "metadata",
            "non-incremental-benchmarks",
            "incremental-benchmarks",
            "benchmarks",
            "default-solver",
            "incremental-solver",
            "solver",
            "all",
        ),
    )
    args = parser.parse_args()
    v = versions()
    if args.component in ("metadata", "all"):
        fetch_metadata(v)
    if args.component in ("benchmarks", "all"):
        fetch_benchmarks(v)
    if args.component == "non-incremental-benchmarks":
        fetch_benchmark_release(v["SMTLIB_NON_INCREMENTAL_RECORD"], "non-incremental")
    if args.component == "incremental-benchmarks":
        fetch_benchmark_release(v["SMTLIB_INCREMENTAL_RECORD"], "incremental")
    if args.component in ("solver", "all"):
        fetch_solver(v)
    if args.component == "default-solver":
        fetch_solver(v, {"default"})
    if args.component == "incremental-solver":
        fetch_solver(v, {"incremental"})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"fetch_official.py: {error}", file=sys.stderr)
        raise SystemExit(1)
