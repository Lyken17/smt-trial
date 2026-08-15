#!/usr/bin/env python3
"""Make the pinned official Dolmen container use its pinned Debian snapshot."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(".cache/smtcomp-tool/external-tools/dolmen/docker/Dockerfile")
DOCKERFILE = Path(".cache/official/external-tools/dolmen/docker/Dockerfile")
MARKER = "# smtcomp-harness: activate the date-pinned Debian snapshot"
NEEDLE = "WORKDIR dolmen/\n\nRUN opam-2.1 install . --deps-only --with-test --yes"
REPLACEMENT = f'''WORKDIR dolmen/

{MARKER}
USER root
RUN sed -i \\
      -e '/snapshot.debian.org/s/^# //' \\
      -e '/deb.debian.org/s/^/# /' \\
      /etc/apt/sources.list \\
    && echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99snapshot \\
    && apt-get update \\
    && apt-get install -y --no-install-recommends libgmp-dev libmpfr-dev pkg-config
USER opam

RUN opam-2.1 install . --deps-only --with-test --yes --assume-depexts'''


def main() -> None:
    text = SOURCE.read_text()
    if NEEDLE not in text:
        raise RuntimeError(f"unexpected official Dolmen Dockerfile: {SOURCE}")
    prepared = text.replace(NEEDLE, REPLACEMENT, 1)
    if DOCKERFILE.is_file() and DOCKERFILE.read_text() == prepared:
        print("Dolmen Dockerfile already uses the pinned Debian snapshot")
        return
    DOCKERFILE.write_text(prepared)
    print("Activated the official base image's 2024-06-12 Debian snapshot")


if __name__ == "__main__":
    main()
