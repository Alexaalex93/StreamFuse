#!/bin/sh
set -e

cd /app

python -m alembic -c alembic.ini upgrade head

if [ "${STREAMFUSE_AUTO_SEED_MOCK:-true}" = "true" ]; then
  if [ "${STREAMFUSE_TAUTULLI_USE_MOCK:-false}" = "true" ] || [ "${STREAMFUSE_SFTPGO_USE_MOCK:-false}" = "true" ]; then
    python -m app.jobs.seed_mock_data
  fi
fi

MODE="${1:-dev}"
if [ "$MODE" = "prod" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${STREAMFUSE_UVICORN_WORKERS:-2}"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "/app/.tmp-test/*"