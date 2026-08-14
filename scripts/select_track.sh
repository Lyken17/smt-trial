#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.cache/system-deps/usr/bin:$PATH"

setup_config="${SETUP_CONFIG:-configs/setup-single-query.env}"
if [[ -f "$setup_config" ]]; then
  # Export only build/storage controls to the official command. They do not
  # alter the official selection inputs or seed.
  set -a
  # shellcheck disable=SC1090
  source "$setup_config"
  set +a
fi
selection_jobs="${SELECTION_JOBS:-auto}"
if [[ "$selection_jobs" == "auto" ]]; then
  selection_jobs="$(nproc 2>/dev/null || echo 4)"
  if (( selection_jobs > 16 )); then
    selection_jobs=16
  fi
fi
if [[ ! "$selection_jobs" =~ ^[1-9][0-9]*$ ]]; then
  echo "SELECTION_JOBS must be auto or a positive integer" >&2
  exit 2
fi

track="${1:?usage: select_track.sh TRACK}"
data=.cache/official/data
benchmarks=.cache/benchmarks
execution=.cache/execution
scrambler=.cache/scrambler/scrambler

if [[ ! -x "$scrambler" ]]; then
  echo "official scrambler is not built; install flex/bison and run make setup" >&2
  exit 2
fi

case "$track" in
  SingleQuery)
    .venv/bin/python scripts/select_single_query.py \
      --data "$data" --benchmarks "$benchmarks" --execution "$execution" \
      --scrambler "$scrambler" --workers "$selection_jobs"
    ;;
  Incremental|ModelValidation|UnsatCore)
    .venv/bin/smtcomp select-and-scramble \
      "$track" "$data" "$benchmarks" "$execution" "$scrambler" \
      --max-workers "$selection_jobs"
    ;;
  Parallel)
    # The official AWS selector produces Cloud and Parallel selections together.
    .venv/bin/smtcomp scramble-aws \
      "$data" "$benchmarks" "$execution" "$scrambler" \
      --max-workers "$selection_jobs"
    ;;
  *)
    echo "unsupported selection track: $track" >&2
    exit 2
    ;;
esac
