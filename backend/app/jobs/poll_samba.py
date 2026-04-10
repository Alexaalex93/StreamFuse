import asyncio

from app.adapters.samba.client import SambaClient, SambaFileProvider
from app.core.config import get_settings
from app.persistence.db import SessionLocal
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver
from app.services.samba_sync_service import SambaSyncService
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService


def _parse_list(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


def _parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


async def run_once() -> dict[str, int]:
    settings = get_settings()
    db = SessionLocal()
    try:
        repo = AppSettingRepository(db)
        enabled_row = repo.get(SettingsService.KEY_SAMBA_ENABLED)
        enabled = _parse_bool(enabled_row.value if enabled_row else str(settings.samba_enabled).lower())
        if not enabled:
            return {"active_imported": 0, "stale_marked": 0, "errors": 0, "total_processed": 0}

        status_path_row = repo.get(SettingsService.KEY_SAMBA_STATUS_JSON_PATH)
        status_path = (status_path_row.value if status_path_row else settings.samba_status_json_path).strip()
        if not status_path:
            return {"active_imported": 0, "stale_marked": 0, "errors": 1, "total_processed": 1}

        mappings_row = repo.get(SettingsService.KEY_SAMBA_PATH_MAPPINGS)
        path_mappings_raw = mappings_row.value if mappings_row else settings.samba_path_mappings
        path_mappings = _parse_list(path_mappings_raw)

        provider = SambaFileProvider(status_path)
        client = SambaClient(provider)
        session_service = SessionService(UnifiedStreamSessionRepository(db))
        sync_service = SambaSyncService(
            client=client,
            session_service=session_service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=settings.samba_stale_seconds,
            path_mappings=path_mappings,
        )
        return await sync_service.poll_once()
    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(run_once())
    print(result)
