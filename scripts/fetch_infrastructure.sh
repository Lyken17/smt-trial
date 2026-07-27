#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT}/versions.env"

TARGET="${ROOT}/.cache/satcomp-infrastructure"
mkdir -p "${ROOT}/.cache"

if [[ ! -d "${TARGET}/.git" ]]; then
  git clone --filter=blob:none --no-checkout "${SATCOMP_REPOSITORY}" "${TARGET}"
fi

git -C "${TARGET}" fetch --depth 1 origin "${SATCOMP_REV}"
git -C "${TARGET}" checkout --detach --force "${SATCOMP_REV}"

echo "Infrastructure ready at ${TARGET}"
echo "Activate it with: source ${TARGET}/satcomp-activate.sh"

