#!/usr/bin/env bash
# One-shot setup for Desktop Automation Using AI
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Creating Python virtual environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing Python packages"
pip install -r requirements.txt

echo "==> Downloading spaCy English model"
python -m spacy download en_core_web_sm || echo "WARNING: spaCy model download failed (rule-based NLP still works)"

echo "==> Optional system packages (Linux)"
if command -v apt-get >/dev/null 2>&1; then
  echo "If OCR / microphone are needed, run:"
  echo "  sudo apt-get update"
  echo "  sudo apt-get install -y tesseract-ocr libportaudio2 portaudio19-dev"
fi

echo "==> Creating data folders"
mkdir -p data/captures data/logs assets/templates

echo "==> Initializing database (first-run seed)"
python - <<'PY'
from src.config import load_config, ensure_runtime_dirs
from src.db.database import get_database
cfg = load_config()
ensure_runtime_dirs(cfg)
db = get_database(cfg)
print("Database ready at", db.db_path)
print("Default login: demo / demo123")
PY

echo ""
echo "Setup complete."
echo "Activate the environment:  source .venv/bin/activate"
echo "Run the app:               python main.py"
