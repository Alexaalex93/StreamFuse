import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider, SFTPGoMockProvider
from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider, TautulliMockProvider
from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService
from app.services.sftpgo_sync_service import SFTPGoSyncService
from app.services.tautulli_sync_service import TautulliSyncService

router = APIRouter(prefix="/internal")


@router.post("/tautulli/import")
async def import_tautulli(
    include_history: bool = Query(default=True),
    use_mock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, int | bool]:
    mock_enabled = settings.tautulli_use_mock if use_mock is None else use_mock
    provider = (
        TautulliMockProvider()
        if mock_enabled
        else TautulliHTTPProvider(settings.tautulli_base_url, settings.tautulli_api_key)
    )

    client = TautulliClient(provider)
    session_service = SessionService(UnifiedStreamSessionRepository(db))
    sync_service = TautulliSyncService(client=client, session_service=session_service)

    result = await sync_service.run_full_import(
        include_history=include_history,
        history_length=settings.tautulli_history_length,
    )
    return {
        **result,
        "used_mock": mock_enabled,
    }


@router.post("/sftpgo/poll")
async def poll_sftpgo(
    use_mock: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, int | bool]:
    mock_enabled = settings.sftpgo_use_mock if use_mock is None else use_mock

    provider = (
        SFTPGoMockProvider()
        if mock_enabled
        else SFTPGoHTTPProvider(
            settings.sftpgo_base_url,
            settings.sftpgo_api_key,
            transfer_log_json_path=(settings.sftpgo_transfer_log_json_path or None),
        )
    )

    client = SFTPGoClient(provider)
    session_service = SessionService(UnifiedStreamSessionRepository(db))
    sync_service = SFTPGoSyncService(
        client=client,
        session_service=session_service,
        poster_resolver=PosterResolver(settings),
        stale_seconds=settings.sftpgo_stale_seconds,
    )
    try:
        result = await sync_service.poll_once(log_limit=settings.sftpgo_log_limit)
    except Exception as exc:
        detail = str(exc)
        raise HTTPException(status_code=502, detail=f"SFTPGo poll failed: {detail}") from exc
    return {
        **result,
        "used_mock": mock_enabled,
    }

