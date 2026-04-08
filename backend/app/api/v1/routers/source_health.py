from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider
from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider
from app.api.deps import get_app_settings
from app.api.v1.schemas.source_health import SourceHealthItem, SourceHealthResponse
from app.core.config import Settings

router = APIRouter(prefix="/sources")


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


@router.get("/health", response_model=SourceHealthResponse)
async def source_health(settings: Settings = Depends(get_app_settings)) -> SourceHealthResponse:
    tautulli = await _check_tautulli(settings)
    sftpgo = await _check_sftpgo(settings)
    return SourceHealthResponse(
        tautulli=tautulli,
        sftpgo=sftpgo,
        updated_at=datetime.now(timezone.utc),
    )
