#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose -f docker-compose.prod.yml up -d --build