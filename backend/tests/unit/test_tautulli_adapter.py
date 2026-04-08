import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.tautulli.client import TautulliClient, TautulliMockProvider
from app.adapters.tautulli.mapper import map_tautulli_payload
from app.domain.enums import MediaType, SessionStatus
from app.persistence.db import Base
from app.persistence.models import unified_stream_session  # noqa: F401
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.session_service import SessionService
from app.services.tautulli_sync_service import TautulliSyncService


def test_map_tautulli_payload_rich_fields() -> None:
    payload = {
        "session_id": "abc123",
        "user": "alice",
        "title": "Dune: Part Two",
        "media_type": "movie",
        "progress_percent": 72.5,
        "duration": 9960000,
        "stream_bitrate": 14500,
        "stream_video_full_resolution": "4K",
        "stream_video_codec": "hevc",
        "stream_audio_codec": "eac3",
        "player": "Plex Web",
        "platform": "Web",
        "ip_address": "192.168.1.10",
        "started": 1710000000,
        "transcode_decision": "direct play",
        "file": "/media/movies/Dune.Part.Two.2024.mkv",
    }

    mapped = map_tautulli_payload(payload, historical=False)

    assert mapped.source_session_id == "abc123"
    assert mapped.user_name == "alice"
    assert mapped.media_type == MediaType.MOVIE
    assert mapped.status == SessionStatus.ACTIVE
    assert mapped.progress_percent == 72.5
    assert mapped.duration_ms == 9960000
    assert mapped.bandwidth_bps == 14500000
    assert mapped.resolution == "4K"
    assert mapped.video_codec == "hevc"
    assert mapped.audio_codec == "eac3"
    assert mapped.player_name == "Plex Web"
    assert mapped.client_name == "Web"
    assert mapped.ip_address == "192.168.1.10"
    assert mapped.transcode_decision == "direct play"
    assert mapped.raw_payload is not None


def test_tautulli_sync_service_imports_mock_sessions() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        repo = UnifiedStreamSessionRepository(db)
        session_service = SessionService(repo)
        client = TautulliClient(TautulliMockProvider())
        sync_service = TautulliSyncService(client=client, session_service=session_service)

        result = asyncio.run(sync_service.run_full_import(include_history=True, history_length=50))

        rows = list(db.scalars(select(UnifiedStreamSessionModel)).all())

        assert result["active_imported"] >= 1
        assert result["history_imported"] >= 1
        assert len(rows) == result["total_imported"]
        assert all(row.source.value == "tautulli" for row in rows)
        assert all(row.raw_payload is not None for row in rows)
    finally:
        db.close()


def test_tautulli_sync_service_skips_bad_payloads(monkeypatch, caplog) -> None:
    class _Provider:
        async def fetch_active_sessions(self):
            return [{"session_id": "ok"}, {"session_id": "broken"}]

        async def fetch_history(self, length: int = 50):
            return []

    engine = create_engine("sqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        repo = UnifiedStreamSessionRepository(db)
        session_service = SessionService(repo)
        client = TautulliClient(_Provider())
        sync_service = TautulliSyncService(client=client, session_service=session_service)

        real_mapper = map_tautulli_payload

        def _faulty_mapper(payload, *, historical=False):
            if payload.get("session_id") == "broken":
                raise ValueError("bad payload")
            return real_mapper(payload, historical=historical)

        monkeypatch.setattr("app.services.tautulli_sync_service.map_tautulli_payload", _faulty_mapper)

        with caplog.at_level("ERROR"):
            imported = asyncio.run(sync_service.import_active_sessions())

        rows = list(db.scalars(select(UnifiedStreamSessionModel)).all())

        assert imported == 1
        assert len(rows) == 1
        assert "Failed to map/store Tautulli active payload" in caplog.text
    finally:
        db.close()