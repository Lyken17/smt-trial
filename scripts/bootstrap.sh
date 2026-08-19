#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source versions.env
set +a

mkdir -p .cache

if [[ ! -d .cache/smtcomp-tool/.git ]]; then
  git clone --filter=blob:none --no-checkout "$SMTCOMP_REPOSITORY" .cache/smtcomp-tool
fi
git -C .cache/smtcomp-tool fetch --depth 1 origin "$SMTCOMP_REV"
git -C .cache/smtcomp-tool sparse-checkout init --cone
git -C .cache/smtcomp-tool sparse-checkout set smtcomp external-tools/dolmen
git -C .cache/smtcomp-tool checkout --detach FETCH_HEAD
git -C .cache/smtcomp-tool show "$SMTCOMP_REV:pyproject.toml" > .cache/smtcomp-tool/pyproject.toml
git -C .cache/smtcomp-tool show "$SMTCOMP_REV:README.md" > .cache/smtcomp-tool/README.md

mkdir -p .cache/official/external-tools
mkdir -p .cache/official/external-tools/dolmen
cp -a .cache/smtcomp-tool/external-tools/dolmen/. .cache/official/external-tools/dolmen/

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
python_marker=.cache/python-install.revision
needs_python_install=false
if [[ ! -x .venv/bin/smtcomp ]] || \
   ! .venv/bin/python -c 'import smtcomp, smtcomp_harness' 2>/dev/null; then
  needs_python_install=true
elif [[ -f "$python_marker" && "$(<"$python_marker")" != "$SMTCOMP_REV" ]]; then
  needs_python_install=true
fi
if [[ "$needs_python_install" == true ]]; then
  .venv/bin/python -m pip install -e . -e .cache/smtcomp-tool
fi
echo "$SMTCOMP_REV" > "$python_marker"
.venv/bin/python scripts/fetch_official.py metadata

if [[ ! -d .cache/scrambler/.git ]]; then
  git clone "$SCRAMBLER_REPOSITORY" .cache/scrambler
fi
git -C .cache/scrambler fetch --depth 1 origin "$SCRAMBLER_REV"
git -C .cache/scrambler checkout --detach FETCH_HEAD
if command -v flex >/dev/null && command -v bison >/dev/null; then
  make -C .cache/scrambler scrambler
else
  echo "WARNING: flex and bison are missing; install them before benchmark selection." >&2
fi

echo "Installed official SMT-COMP tool at $SMTCOMP_REV"
echo "Checked out official scrambler at $SCRAMBLER_REV"
