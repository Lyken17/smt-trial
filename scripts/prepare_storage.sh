#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

config="${1:-configs/setup-all.env}"
# shellcheck disable=SC1090
source "$config"

raw_benchmarks="$PWD/.cache/benchmarks/non-incremental"
selected_benchmarks="$PWD/.cache/execution/benchmarks"
mkdir -p "$raw_benchmarks" "$(dirname "$selected_benchmarks")"

placement="${CACHE_PLACEMENT:-auto}"
external_root="${EXTERNAL_CACHE_ROOT:-}"
case "$placement" in
  auto) ;;
  local)
    if [[ -n "$external_root" ]]; then
      echo "EXTERNAL_CACHE_ROOT must be empty when CACHE_PLACEMENT=local" >&2
      exit 2
    fi
    ;;
  external)
    if [[ -z "$external_root" ]]; then
      echo "EXTERNAL_CACHE_ROOT is required when CACHE_PLACEMENT=external" >&2
      exit 2
    fi
    ;;
  *)
    echo "CACHE_PLACEMENT must be auto, local, or external" >&2
    exit 2
    ;;
esac
if [[ -z "$external_root" && "$placement" == "auto" ]] \
  && grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null \
  && [[ "$(stat -f -c %T "$PWD")" == "9p" || "$(stat -f -c %T "$PWD")" == "drvfs" ]]; then
  external_root="${XDG_CACHE_HOME:-${HOME:?HOME is required}/.cache}/smtcomp-2025-cvc5"
fi
if [[ -n "$external_root" && "$external_root" != /* ]]; then
  echo "EXTERNAL_CACHE_ROOT must be an absolute path: $external_root" >&2
  exit 2
fi
if [[ "$external_root" == "/" ]]; then
  echo "EXTERNAL_CACHE_ROOT must not be the filesystem root" >&2
  exit 2
fi

ensure_cache_location() {
  local link="$1"
  local target="$2"
  if [[ -L "$link" ]]; then
    local current
    current="$(readlink "$link")"
    if [[ "$current" != /* ]]; then
      current="$(realpath -m "$(dirname "$link")/$current")"
    fi
    mkdir -p "$current"
    if [[ "$placement" == "external" && "$current" != "$(realpath -m "$target")" ]]; then
      echo "$link points to an unexpected cache location" >&2
      exit 2
    fi
  elif [[ -e "$link" ]]; then
    return
  elif [[ -n "$target" ]]; then
    mkdir -p "$target"
    ln -s "$target" "$link"
  else
    mkdir -p "$link"
  fi
}

selection_target="${external_root:+$external_root/execution/benchmarks}"
ensure_cache_location "$selected_benchmarks" "$selection_target"

destinations=("$raw_benchmarks")
if [[ ! -L "$selected_benchmarks" ]]; then
  destinations+=("$selected_benchmarks")
fi

# The largest archive is much faster to unpack on WSL's native Linux
# filesystem.  The official directory layout remains visible below .cache, so
# selection and scoring use exactly the same paths and bytes on every host.
if [[ -n "${LARGE_LOGIC:-}" ]]; then
  logic_link="$PWD/.cache/benchmarks/non-incremental/$LARGE_LOGIC"
  logic_target="${external_root:+$external_root/benchmarks/non-incremental/$LARGE_LOGIC}"
  ensure_cache_location "$logic_link" "$logic_target"
fi

available_kib="$(df -Pk "$PWD" | awk 'NR==2 {print $4}')"
required_kib="$((MIN_FREE_GIB * 1024 * 1024))"

if (( available_kib >= required_kib )); then
  exit 0
fi

if [[ "$NTFS_COMPRESSION" == "auto" ]] \
  && command -v compact.exe >/dev/null \
  && command -v wslpath >/dev/null; then
  for destination in "${destinations[@]}"; do
    compact.exe /C /I /Q "$(wslpath -w "$destination")"
  done
  echo "Enabled NTFS compression for benchmark and selection directories; only ${available_kib} KiB were free."
  exit 0
fi

echo "Insufficient disk space for the official non-incremental release." >&2
echo "Need at least ${MIN_FREE_GIB} GiB free, or NTFS compression under WSL; have $((available_kib / 1024 / 1024)) GiB." >&2
exit 2
