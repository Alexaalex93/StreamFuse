import asyncio

from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider, SFTPGoMockProvider
from app.core.config import get_settings
from app.persistence.db import SessionLocal
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService
from app.services.sftpgo_sync_service import SFTPGoSyncService


def _parse_list(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


async def run_once() -> dict[str, int]:
    settings = get_settings()

    provider = (
        SFTPGoMockProvider()
        if settings.sftpgo_use_mock
        else SFTPGoHTTPProvider(
            settings.sftpgo_base_url,
            settings.sftpgo_api_key,
            transfer_log_json_path=(settings.sftpgo_transfer_log_json_path or None),
        )
    )

    client = SFTPGoClient(provider)
    db = SessionLocal()
    try:
        path_mapping_row = AppSettingRepository(db).get(SettingsService.KEY_SFTPGO_PATH_MAPPINGS)
        path_mappings_raw = path_mapping_row.value if path_mapping_row else settings.sftpgo_path_mappings
        path_mappings = _parse_list(path_mappings_raw)

        session_service = SessionService(UnifiedStreamSessionRepository(db))
        sync_service = SFTPGoSyncService(
            client=client,
            session_service=session_service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=settings.sftpgo_stale_seconds,
            path_mappings=path_mappings,
        )
        return await sync_service.poll_once(log_limit=settings.sftpgo_log_limit)
    finally:
        db.close()


if __name__ == "__main__":
    result = asyncio.run(run_once())
    print(result)
