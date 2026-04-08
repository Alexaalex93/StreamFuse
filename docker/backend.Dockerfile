FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/alembic.ini /app/alembic.ini
COPY backend/app /app/app
COPY docker/scripts/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh

RUN chmod +x /usr/local/bin/backend-entrypoint.sh \
    && pip install --upgrade pip \
    && pip install -e .

EXPOSE 8000

FROM base AS dev
CMD ["backend-entrypoint.sh", "dev"]

FROM base AS prod
CMD ["backend-entrypoint.sh", "prod"]