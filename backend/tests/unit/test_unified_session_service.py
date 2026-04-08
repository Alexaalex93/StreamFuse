from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.persistence.db import Base
from app.persistence.models import unified_stream_session  # noqa: F401
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.unified_session_service import UnifiedSessionService


def _setup_service(stale_seconds: int = 180):
    engine = create_engine("sqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    repo = UnifiedStreamSessionRepository(db)
    service = UnifiedSessionService(repo, stale_seconds=stale_seconds)
    return db, repo, service


def _session(
    *,
    source: StreamSource,
    source_session_id: str,
    user_name: str,
    media_type: MediaType,
    status: SessionStatus = SessionStatus.ACTIVE,
    started_at: datetime | None = None,
) -> UnifiedStreamSessionCreate:
    return UnifiedStreamSessionCreate(
        source=source,
        source_session_id=source_session_id,
        status=status,
        user_name=user_name,
        title=f"title-{source_session_id}",
        title_clean=f"title-{source_session_id}",
        media_type=media_type,
        started_at=started_at or datetime.now(timezone.utc),
    )


def test_different_sources_are_not_merged() -> None:
    db, repo, service = _setup_service()
    try:
        tautulli = _session(
            source=StreamSource.TAUTULLI,
            source_session_id="same-id",
            user_name="alex",
            media_type=MediaType.MOVIE,
        )
        sftpgo = _session(
            source=StreamSource.SFTPGO,
            source_session_id="same-id",
            user_name="alex",
            media_type=MediaType.EPISODE,
        )

        assert service.ingest_tautulli_sessions([tautulli]) == 1
        assert service.ingest_sftpgo_sessions([sftpgo]) == 1

        active = service.get_active_sessions()
        assert len(active) == 2
        assert {row.source for row in active} == {StreamSource.TAUTULLI, StreamSource.SFTPGO}
    finally:
        db.close()


def test_active_filters_user_source_media_type_and_dates() -> None:
    db, repo, service = _setup_service()
    try:
        base_date = datetime(2026, 4, 1, tzinfo=timezone.utc)

        rows = [
            _session(
                source=StreamSource.TAUTULLI,
                source_session_id="t1",
                user_name="alice",
                media_type=MediaType.MOVIE,
                started_at=base_date,
            ),
            _session(
                source=StreamSource.SFTPGO,
                source_session_id="s1",
                user_name="alice",
                media_type=MediaType.EPISODE,
                started_at=base_date + timedelta(days=1),
            ),
            _session(
                source=StreamSource.SFTPGO,
                source_session_id="s2",
                user_name="bob",
                media_type=MediaType.FILE_TRANSFER,
                started_at=base_date + timedelta(days=2),
            ),
        ]

        service.ingest_tautulli_sessions([rows[0]])
        service.ingest_sftpgo_sessions(rows[1:])

        filtered = service.get_active_sessions(
            user_name="alice",
            source=StreamSource.SFTPGO,
            media_type=MediaType.EPISODE,
            date_from=base_date + timedelta(hours=12),
            date_to=base_date + timedelta(days=1, hours=12),
        )

        assert len(filtered) == 1
        assert filtered[0].source_session_id == "s1"
    finally:
        db.close()


def test_mark_stale_moves_session_to_history() -> None:
    db, repo, service = _setup_service(stale_seconds=0)
    try:
        row = _session(
            source=StreamSource.SFTPGO,
            source_session_id="stale-1",
            user_name="stale-user",
            media_type=MediaType.FILE_TRANSFER,
        )
        service.ingest_sftpgo_sessions([row])

        count = service.mark_stale_sessions(source=StreamSource.SFTPGO)
        assert count == 1

        active = service.get_active_sessions(source=StreamSource.SFTPGO)
        history = service.get_history(source=StreamSource.SFTPGO)

        assert len(active) == 0
        assert len(history) == 1
        assert history[0].status == SessionStatus.ENDED
        assert isinstance(history[0].raw_payload, dict)
        assert history[0].raw_payload.get("lifecycle") == "stale"
    finally:
        db.close()
