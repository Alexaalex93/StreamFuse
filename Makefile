.PHONY: backend-install frontend-install backend-dev frontend-dev dev test lint format db-upgrade db-seed import-tautulli poll-sftpgo

backend-install:
	cd backend && pip install -e .[dev]

frontend-install:
	cd frontend && npm install

backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

dev:
	docker compose up --build

db-upgrade:
	cd backend && python -m alembic -c alembic.ini upgrade head

db-seed:
	cd backend && python -m app.jobs.seed_mock_data

import-tautulli:
	cd backend && python -m app.jobs.import_tautulli

poll-sftpgo:
	cd backend && python -m app.jobs.poll_sftpgo

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format
