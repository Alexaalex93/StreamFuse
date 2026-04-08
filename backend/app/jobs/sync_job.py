import asyncio

from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoHTTPProvider, SFTPGoMockProvider
from app.adapters.tautulli.client import TautulliClient, TautulliHTTPProvider, TautulliMockProvider
from app.core.config import get_settings
from app.services.sync_service import SyncService


async def run_once() -> dict[str, int]:
    settings = get_settings()

    tautulli_provider = (
        TautulliMockProvider()
        if settings.tautulli_use_mock
        else TautulliHTTPProvider(settings.tautulli_base_url, settings.tautulli_api_key)
    )

    sftpgo_provider = (
        SFTPGoMockProvider()
        if settings.sftpgo_use_mock
        else SFTPGoHTTPProvider(
            settings.sftpgo_base_url,
            settings.sftpgo_api_key,
            transfer_log_json_path=(settings.sftpgo_transfer_log_json_path or None),
        )
    )

    service = SyncService(
        tautulli_client=TautulliClient(tautulli_provider),
        sftpgo_client=SFTPGoClient(sftpgo_provider),
    )
    return await service.run_sync()


if __name__ == "__main__":
    result = asyncio.run(run_once())
    print(result)
