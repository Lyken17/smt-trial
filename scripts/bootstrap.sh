#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT}/versions.env"

TOOLS_ONLY=false
if [[ "${1:-}" == "--tools-only" ]]; then
  TOOLS_ONLY=true
fi

VENV="${ROOT}/.venv"
SOURCE_DIR="${ROOT}/.cache/cvc5-src"
BUILD_DIR="${ROOT}/.cache/cvc5-build"

if [[ ! -x "${VENV}/bin/python" ]]; then
  python3 -m venv "${VENV}"
fi
"${VENV}/bin/python" -m pip install --disable-pip-version-check \
  -r "${ROOT}/requirements-dev.txt"

if "${TOOLS_ONLY}"; then
  exit 0
fi

compiler_major="$(
  g++ -dumpfullversion -dumpversion 2>/dev/null | cut -d. -f1 || true
)"
if [[ -z "${compiler_major}" || "${compiler_major}" -lt 10 ]]; then
  if type module >/dev/null 2>&1; then
    module load gcc/13.1.0
  fi
fi

compiler_major="$(
  g++ -dumpfullversion -dumpversion 2>/dev/null | cut -d. -f1 || true
)"
if [[ -z "${compiler_major}" || "${compiler_major}" -lt 10 ]]; then
  echo "cvc5 requires GCC >= 10 or Clang >= 12; found: $(g++ --version | head -1)" >&2
  exit 1
fi

export CC="$(command -v gcc)"
export CXX="$(command -v g++)"

mkdir -p "${ROOT}/.cache"
if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  git clone --filter=blob:none --no-checkout "${CVC5_REPOSITORY}" "${SOURCE_DIR}"
fi

git -C "${SOURCE_DIR}" fetch --depth 1 origin "${CVC5_REV}"
git -C "${SOURCE_DIR}" checkout --detach --force "${CVC5_REV}"

export PATH="${VENV}/bin:${PATH}"
(
  cd "${SOURCE_DIR}"
  ./configure.sh competition \
    --auto-download \
    --ninja \
    --static \
    "-DCMAKE_C_COMPILER=${CC}" \
    "-DCMAKE_CXX_COMPILER=${CXX}" \
    --name="${BUILD_DIR}"
)

cmake --build "${BUILD_DIR}" --parallel "${BUILD_JOBS:-$(nproc)}" --target cvc5-bin
"${BUILD_DIR}/bin/cvc5" --version
