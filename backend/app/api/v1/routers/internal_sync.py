import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.adapters.samba.client import SambaClient, SambaFileProvider
from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider, SFTPGoMockProvider
from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider, TautulliMockProvider
from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver
from app.services.samba_sync_service import SambaSyncService
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService
from app.services.sftpgo_sync_service import SFTPGoSyncService
from app.services.tautulli_sync_service import TautulliSyncService

router = APIRouter(prefix="/internal")


def _parse_list(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


def _parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


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

    setting_repo = AppSettingRepository(db)
    custom_mapping_row = setting_repo.get(SettingsService.KEY_SFTPGO_PATH_MAPPINGS)
    mapping_raw = custom_mapping_row.value if custom_mapping_row else settings.sftpgo_path_mappings
    path_mappings = _parse_list(mapping_raw)

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
        path_mappings=path_mappings,
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


@router.post("/samba/poll")
async def poll_samba(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, int | bool]:
    setting_repo = AppSettingRepository(db)

    enabled_row = setting_repo.get(SettingsService.KEY_SAMBA_ENABLED)
    samba_enabled = _parse_bool(enabled_row.value if enabled_row else str(settings.samba_enabled).lower())
    if not samba_enabled:
        return {
            "active_imported": 0,
            "stale_marked": 0,
            "errors": 0,
            "total_processed": 0,
            "enabled": False,
        }

    status_path_row = setting_repo.get(SettingsService.KEY_SAMBA_STATUS_JSON_PATH)
    status_json_path = (status_path_row.value if status_path_row else settings.samba_status_json_path).strip()
    if not status_json_path:
        raise HTTPException(status_code=422, detail="Samba status JSON path is not configured")

    mappings_row = setting_repo.get(SettingsService.KEY_SAMBA_PATH_MAPPINGS)
    mappings_raw = mappings_row.value if mappings_row else settings.samba_path_mappings
    path_mappings = _parse_list(mappings_raw)

    provider = SambaFileProvider(status_json_path)
    client = SambaClient(provider)
    session_service = SessionService(UnifiedStreamSessionRepository(db))
    sync_service = SambaSyncService(
        client=client,
        session_service=session_service,
        poster_resolver=PosterResolver(settings),
        stale_seconds=settings.samba_stale_seconds,
        path_mappings=path_mappings,
    )

    try:
        result = await sync_service.poll_once()
    except Exception as exc:
        detail = str(exc)
        raise HTTPException(status_code=502, detail=f"Samba poll failed: {detail}") from exc

    return {
        **result,
        "enabled": True,
    }
