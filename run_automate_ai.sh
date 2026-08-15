#!/usr/bin/env bash
set -euo pipefail
ROOT="/workspace"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"
exec python "$ROOT/main.py"
