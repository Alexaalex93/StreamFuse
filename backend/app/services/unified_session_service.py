from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, StreamSource
from app.persistence.repositories.unified_stream_session_repository import (
    SessionQueryFilters,
    UnifiedStreamSessionRepository,
)


class UnifiedSessionService:
    def __init__(self, repository: UnifiedStreamSessionRepository, stale_seconds: int = 180) -> None:
        self.repository = repository
        self.stale_seconds = stale_seconds

    def get_active_sessions(
        self,
        *,
        user_name: str | None = None,
        source: StreamSource | None = None,
        media_type: MediaType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
    ):
        filters = SessionQueryFilters(
            user_name=user_name,
            source=source,
            media_type=media_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return self.repository.list_active(filters)

    def get_history(
        self,
        *,
        user_name: str | None = None,
        source: StreamSource | None = None,
        media_type: MediaType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 200,
    ):
        filters = SessionQueryFilters(
            user_name=user_name,
            source=source,
            media_type=media_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return self.repository.list_history(filters)

    def ingest_tautulli_sessions(self, sessions: list[UnifiedStreamSessionCreate]) -> int:
        count = 0
        for session in sessions:
            if session.source != StreamSource.TAUTULLI:
                continue
            self.repository.create(session)
            count += 1
        return count

    def ingest_sftpgo_sessions(self, sessions: list[UnifiedStreamSessionCreate]) -> int:
        count = 0
        for session in sessions:
            if session.source != StreamSource.SFTPGO:
                continue
            self.repository.create(session)
            count += 1
        return count

    def mark_stale_sessions(self, source: StreamSource | None = None) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_seconds)
        return self.repository.mark_active_as_stale(cutoff=cutoff, source=source)
