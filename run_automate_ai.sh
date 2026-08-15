#!/usr/bin/env bash
# Double-click / terminal launcher for Automate AI
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -f "$ROOT/.venv/bin/activate" ]]; then
  echo "Virtual environment missing. Run: ./scripts/install_desktop.sh"
  exit 1
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
exec python "$ROOT/main.py"
