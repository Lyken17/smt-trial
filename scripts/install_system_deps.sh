#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

config="${1:-configs/setup-all.env}"
if [[ ! -f "$config" ]]; then
  echo "dependency configuration not found: $config" >&2
  exit 2
fi

# shellcheck disable=SC1090
source "$config"
if (( ${#APT_PACKAGES[@]} == 0 )); then
  echo "APT_PACKAGES is empty in $config" >&2
  exit 2
fi

install_with_apt=false
if command -v apt-get >/dev/null; then
  if (( EUID == 0 )); then
    apt-get update
    apt-get install -y "${APT_PACKAGES[@]}"
    install_with_apt=true
  elif command -v sudo >/dev/null && sudo -n true 2>/dev/null; then
    sudo apt-get update
    sudo apt-get install -y "${APT_PACKAGES[@]}"
    install_with_apt=true
  elif command -v sudo >/dev/null && [[ -t 0 && -t 1 ]]; then
    echo "System dependencies require administrator access; sudo may prompt for this user's password."
    sudo apt-get update
    sudo apt-get install -y "${APT_PACKAGES[@]}"
    install_with_apt=true
  fi
fi

missing=()
for command_name in "${REQUIRED_COMMANDS[@]}"; do
  command -v "$command_name" >/dev/null || missing+=("$command_name")
done
if ! python3 -c 'import venv' >/dev/null 2>&1; then
  missing+=("python3-venv")
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
  missing+=("python>=3.11")
fi

if (( ${#missing[@]} > 0 )); then
  echo "Missing required host tools: ${missing[*]}" >&2
  if [[ "$install_with_apt" == false ]]; then
    echo "Install the packages listed in $config with this host's package manager." >&2
    echo "On Debian/Ubuntu, rerun make system-deps in an interactive terminal with sudo access." >&2
  fi
  exit 2
fi

# Docker packages create a daemon socket owned by the docker group. For the
# all-Track setup, enroll the invoking user so the official Dolmen build works
# in the same make invocation (the Makefile uses `sg docker` until next login).
if [[ " ${REQUIRED_COMMANDS[*]} " == *" docker "* ]] && (( EUID != 0 )); then
  if command -v systemctl >/dev/null && command -v sudo >/dev/null \
      && ! sudo -n docker info >/dev/null 2>&1; then
    if sudo -n true 2>/dev/null || [[ -t 0 && -t 1 ]]; then
      sudo systemctl start docker
    fi
  fi
  if getent group docker >/dev/null && ! id -nG "$USER" | tr ' ' '\n' | grep -qx docker; then
    if command -v sudo >/dev/null && (sudo -n true 2>/dev/null || [[ -t 0 && -t 1 ]]); then
      sudo usermod -aG docker "$USER"
    else
      echo "Docker is installed, but $USER is not in the docker group." >&2
      echo "Run: sudo usermod -aG docker \"\$USER\"" >&2
      exit 2
    fi
  fi
fi

echo "System dependency check passed."
