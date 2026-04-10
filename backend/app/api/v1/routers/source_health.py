from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.samba.client import SambaClient, SambaFileProvider
from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider
from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider
from app.api.deps import get_app_settings, get_db
from app.api.v1.schemas.source_health import SourceHealthItem, SourceHealthResponse
from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/sources")


def _parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


async def _check_tautulli(settings: Settings) -> SourceHealthItem:
    if settings.tautulli_use_mock:
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="mock mode enabled")

    if not settings.tautulli_base_url or not settings.tautulli_api_key or settings.tautulli_api_key == "changeme":
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="missing URL or API key")

    try:
        provider = TautulliHTTPProvider(settings.tautulli_base_url, settings.tautulli_api_key, timeout_seconds=6.0)
        client = TautulliClient(provider)
        await client.fetch_active_sessions()
        return SourceHealthItem(configured=True, connected=True, status="connected")
    except Exception as exc:  # noqa: BLE001
        return SourceHealthItem(configured=True, connected=False, status="disconnected", reason=str(exc))


async def _check_sftpgo(settings: Settings) -> SourceHealthItem:
    if settings.sftpgo_use_mock:
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="mock mode enabled")

    if not settings.sftpgo_base_url or not settings.sftpgo_api_key or settings.sftpgo_api_key == "changeme":
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="missing URL or API key")

    try:
        provider = SFTPGoHTTPProvider(settings.sftpgo_base_url, settings.sftpgo_api_key, timeout_seconds=6.0)
        client = SFTPGoClient(provider)
        await client.fetch_active_connections()
        return SourceHealthItem(configured=True, connected=True, status="connected")
    except Exception as exc:  # noqa: BLE001
        return SourceHealthItem(configured=True, connected=False, status="disconnected", reason=str(exc))


async def _check_samba(settings: Settings, db: Session) -> SourceHealthItem:
    repo = AppSettingRepository(db)
    enabled_row = repo.get(SettingsService.KEY_SAMBA_ENABLED)
    path_row = repo.get(SettingsService.KEY_SAMBA_STATUS_JSON_PATH)

    samba_enabled = _parse_bool(enabled_row.value if enabled_row else str(settings.samba_enabled).lower())
    status_path = (path_row.value if path_row else settings.samba_status_json_path).strip()

    if not samba_enabled:
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="disabled")

    if not status_path:
        return SourceHealthItem(configured=False, connected=False, status="disconnected", reason="missing status JSON path")

    try:
        provider = SambaFileProvider(status_path)
        client = SambaClient(provider)
        await client.fetch_active_connections()
        return SourceHealthItem(configured=True, connected=True, status="connected")
    except Exception as exc:  # noqa: BLE001
        return SourceHealthItem(configured=True, connected=False, status="disconnected", reason=str(exc))


@router.get("/health", response_model=SourceHealthResponse)
async def source_health(
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
) -> SourceHealthResponse:
    tautulli = await _check_tautulli(settings)
    sftpgo = await _check_sftpgo(settings)
    samba = await _check_samba(settings, db)
    return SourceHealthResponse(
        tautulli=tautulli,
        sftpgo=sftpgo,
        samba=samba,
        updated_at=datetime.now(timezone.utc),
    )
