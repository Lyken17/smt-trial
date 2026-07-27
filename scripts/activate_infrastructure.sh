#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Source this script so its environment changes persist:" >&2
  echo "  source scripts/activate_infrastructure.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRASTRUCTURE="${ROOT}/.cache/satcomp-infrastructure"

if [[ ! -f "${INFRASTRUCTURE}/satcomp-activate.sh" ]]; then
  "${ROOT}/scripts/fetch_infrastructure.sh" || return 1
fi

export CVC5_CLOUD_ROOT="${ROOT}"
source "${INFRASTRUCTURE}/satcomp-activate.sh"
