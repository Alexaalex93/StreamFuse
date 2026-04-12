import asyncio
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routers import dashboard, unified_sessions
from app.api.v1.routers import auth, health, history, internal_sync, posters, sessions, settings, source_health, stats, system
from app.core.config import get_settings
from app.jobs.background_sync import BackgroundSyncRunner

logger = logging.getLogger(__name__)


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

    # Legacy endpoints kept open for compatibility (e.g. Unraid widget).
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(unified_sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])
    app.include_router(posters.router, prefix="/api", tags=["posters"])
    app.include_router(settings.router, prefix="/api", tags=["settings"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(source_health.router, prefix="/api", tags=["source-health"])

    # Protected API v1
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"], dependencies=[Depends(get_current_user)])
    app.include_router(unified_sessions.router, prefix="/api/v1/sessions", tags=["sessions"], dependencies=[Depends(get_current_user)])
    app.include_router(history.router, prefix="/api/v1", tags=["history"], dependencies=[Depends(get_current_user)])
    app.include_router(stats.router, prefix="/api/v1", tags=["stats"], dependencies=[Depends(get_current_user)])
    app.include_router(posters.router, prefix="/api/v1", tags=["posters"])
    app.include_router(internal_sync.router, prefix="/api/v1", tags=["internal-sync"], dependencies=[Depends(get_current_user)])
    app.include_router(settings.router, prefix="/api/v1", tags=["settings"], dependencies=[Depends(get_current_user)])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"], dependencies=[Depends(get_current_user)])
    app.include_router(source_health.router, prefix="/api/v1", tags=["source-health"], dependencies=[Depends(get_current_user)])
    app.include_router(system.router, prefix="/api/v1", tags=["system"], dependencies=[Depends(get_current_user)])

    @app.on_event("startup")
    async def _startup_background_sync() -> None:
        if not app_settings.background_sync_enabled:
            logger.info("Background sync is disabled")
            return

        runner = BackgroundSyncRunner()
        task = asyncio.create_task(runner.run_forever(), name="streamfuse-background-sync")
        app.state.background_sync_runner = runner
        app.state.background_sync_task = task
        logger.info("Background sync task started")

    @app.on_event("shutdown")
    async def _shutdown_background_sync() -> None:
        runner = getattr(app.state, "background_sync_runner", None)
        task = getattr(app.state, "background_sync_task", None)

        if runner is not None:
            runner.stop()

        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except TimeoutError:
                task.cancel()
            except Exception:
                logger.exception("Error while stopping background sync task")

    return app


app = create_app()





