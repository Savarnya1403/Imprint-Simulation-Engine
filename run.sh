#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-../.venv/bin/python}"
PORT="${PORT:-7777}"

if [ ! -x "$PY" ]; then
  PY="$(command -v python3.11 || command -v python3)"
  echo "No local venv found. Create one once with:"
  echo "  python3.11 -m venv ../.venv"
  echo "  ../.venv/bin/pip install -r requirements.txt"
  echo
  echo "Falling back to $PY for this run; TimesFM may be unavailable."
fi

echo "Imprint Bharat · http://127.0.0.1:${PORT}"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
