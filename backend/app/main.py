from fastapi import FastAPI

from app.api.routers import dashboard, unified_sessions
from app.api.v1.routers import (
    health,
    history,
    internal_sync,
    posters,
    sessions,
    settings,
    stats,
)
from app.core.config import get_settings


def create_app() -> FastAPI:
    app_settings = get_settings()
    app = FastAPI(title="StreamFuse API", version="0.1.0", debug=app_settings.debug)

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(unified_sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])
    app.include_router(settings.router, prefix="/api", tags=["settings"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
    app.include_router(history.router, prefix="/api/v1", tags=["history"])
    app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
    app.include_router(posters.router, prefix="/api/v1", tags=["posters"])
    app.include_router(internal_sync.router, prefix="/api/v1", tags=["internal-sync"])
    app.include_router(settings.router, prefix="/api/v1", tags=["settings"])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])

    return app


app = create_app()