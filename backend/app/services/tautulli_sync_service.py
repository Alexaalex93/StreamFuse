from __future__ import annotations

import logging

from app.adapters.tautulli.client import TautulliClient
from app.adapters.tautulli.mapper import map_tautulli_payload
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class TautulliSyncService:
    def __init__(self, client: TautulliClient, session_service: SessionService) -> None:
        self.client = client
        self.session_service = session_service

    async def import_active_sessions(self) -> int:
        rows = await self.client.fetch_active_sessions()
        imported = 0
        for payload in rows:
            try:
                mapped = map_tautulli_payload(payload, historical=False)
                self.session_service.create_session(mapped)
                imported += 1
            except Exception:
                logger.exception("Failed to map/store Tautulli active payload")
        return imported

    async def import_history(self, length: int = 100) -> int:
        rows = await self.client.fetch_history(length=length)
        imported = 0
        for payload in rows:
            try:
                mapped = map_tautulli_payload(payload, historical=True)
                self.session_service.create_session(mapped)
                imported += 1
            except Exception:
                logger.exception("Failed to map/store Tautulli history payload")
        return imported

    async def run_full_import(self, include_history: bool = True, history_length: int = 100) -> dict[str, int]:
        active_count = await self.import_active_sessions()
        history_count = 0
        if include_history:
            history_count = await self.import_history(length=history_length)

        return {
            "active_imported": active_count,
            "history_imported": history_count,
            "total_imported": active_count + history_count,
        }