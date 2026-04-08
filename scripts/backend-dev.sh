#!/usr/bin/env bash
set -euo pipefail

cd backend
python -m venv .venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
