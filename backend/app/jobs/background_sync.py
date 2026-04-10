import asyncio
import logging

from app.core.config import get_settings
from app.jobs.import_tautulli import run_once as run_tautulli_import
from app.jobs.poll_samba import run_once as run_samba_poll
from app.jobs.poll_sftpgo import run_once as run_sftpgo_poll
from app.persistence.db import SessionLocal
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class BackgroundSyncRunner:
    def __init__(self) -> None:
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        logger.info("Background sync runner started")
        while not self._stop_event.is_set():
            try:
                tautulli_result = await run_tautulli_import(include_history=False)
                sftpgo_result = await run_sftpgo_poll()
                samba_result = await run_samba_poll()
                logger.info(
                    "Background sync cycle completed",
                    extra={"tautulli": tautulli_result, "sftpgo": sftpgo_result, "samba": samba_result},
                )
            except Exception:
                logger.exception("Background sync cycle failed")

            interval = self._resolve_polling_interval()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except TimeoutError:
                continue

        logger.info("Background sync runner stopped")

    def _resolve_polling_interval(self) -> int:
        settings = get_settings()
        default_interval = 30

        db = SessionLocal()
        try:
            row = AppSettingRepository(db).get(SettingsService.KEY_POLLING_FREQUENCY_SECONDS)
            if row and row.value:
                try:
                    return max(5, int(row.value))
                except ValueError:
                    return default_interval
        finally:
            db.close()

        env_value = getattr(settings, "background_sync_interval_seconds", None)
        if isinstance(env_value, int):
            return max(5, env_value)

        return default_interval
