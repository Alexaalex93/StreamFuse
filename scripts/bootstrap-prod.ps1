if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}

docker compose -f docker-compose.prod.yml up -d --build