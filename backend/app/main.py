from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import dashboard, unified_sessions
from app.api.v1.routers import (
    health,
    history,
    internal_sync,
    posters,
    sessions,
    settings,
    source_health,
    stats,
)
from app.core.config import get_settings


def _parse_cors_origins(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_app() -> FastAPI:
    app_settings = get_settings()
    app = FastAPI(title="StreamFuse API", version="0.1.0", debug=app_settings.debug)

    cors_origins = _parse_cors_origins(app_settings.cors_origins)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(unified_sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])
    app.include_router(settings.router, prefix="/api", tags=["settings"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(source_health.router, prefix="/api", tags=["source-health"])

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
    app.include_router(history.router, prefix="/api/v1", tags=["history"])
    app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
    app.include_router(posters.router, prefix="/api/v1", tags=["posters"])
    app.include_router(internal_sync.router, prefix="/api/v1", tags=["internal-sync"])
    app.include_router(settings.router, prefix="/api/v1", tags=["settings"])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
    app.include_router(source_health.router, prefix="/api/v1", tags=["source-health"])

    return app


app = create_app()
