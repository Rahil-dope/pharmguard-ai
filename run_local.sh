#!/usr/bin/env bash
# Development convenience: venv, install backend deps, run backend from project root.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r backend/requirements.txt
export DATA_DIR="${DATA_DIR:-$ROOT/data}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-$ROOT/data/pharmguard.db}"
cd backend && exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
