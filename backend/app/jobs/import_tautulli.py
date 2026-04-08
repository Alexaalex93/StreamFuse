import asyncio

from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider, TautulliMockProvider
from app.core.config import get_settings
from app.persistence.db import SessionLocal
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.session_service import SessionService
from app.services.tautulli_sync_service import TautulliSyncService


async def run_once(include_history: bool = True) -> dict[str, int]:
    settings = get_settings()

    provider = (
        TautulliMockProvider()
        if settings.tautulli_use_mock
        else TautulliHTTPProvider(settings.tautulli_base_url, settings.tautulli_api_key)
    )
    client = TautulliClient(provider)

    db = SessionLocal()
    try:
        session_service = SessionService(UnifiedStreamSessionRepository(db))
        sync_service = TautulliSyncService(client=client, session_service=session_service)
        return await sync_service.run_full_import(
            include_history=include_history,
            history_length=settings.tautulli_history_length,
        )
    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(run_once())
    print(result)
