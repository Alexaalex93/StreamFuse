from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, StreamSource
from app.main import app
from app.persistence.db import Base
from app.persistence.models import unified_stream_session  # noqa: F401
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.unified_session_service import UnifiedSessionService


def test_api_active_and_history_filters() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        db = SessionLocal()
        service = UnifiedSessionService(UnifiedStreamSessionRepository(db), stale_seconds=0)

        service.ingest_tautulli_sessions(
            [
                UnifiedStreamSessionCreate(
                    source=StreamSource.TAUTULLI,
                    source_session_id="t-api-1",
                    user_name="alice",
                    title="Movie A",
                    title_clean="movie a",
                    media_type=MediaType.MOVIE,
                    started_at=datetime.now(timezone.utc),
                )
            ]
        )
        service.ingest_sftpgo_sessions(
            [
                UnifiedStreamSessionCreate(
                    source=StreamSource.SFTPGO,
                    source_session_id="s-api-1",
                    user_name="bob",
                    title="Episode B",
                    title_clean="episode b",
                    media_type=MediaType.EPISODE,
                    started_at=datetime.now(timezone.utc),
                )
            ]
        )
        service.mark_stale_sessions(source=StreamSource.SFTPGO)
        db.close()

        client = TestClient(app)

        active = client.get("/api/sessions/active", params={"source": "tautulli"})
        history = client.get("/api/sessions/history", params={"source": "sftpgo"})

        assert active.status_code == 200
        assert history.status_code == 200

        active_rows = active.json()
        history_rows = history.json()

        assert len(active_rows) == 1
        assert active_rows[0]["source"] == "tautulli"

        assert len(history_rows) == 1
        assert history_rows[0]["source"] == "sftpgo"
    finally:
        app.dependency_overrides.clear()


def test_v1_sessions_endpoint_returns_only_active_and_honors_source_filter() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        db = SessionLocal()
        service = UnifiedSessionService(UnifiedStreamSessionRepository(db), stale_seconds=0)
        service.ingest_tautulli_sessions(
            [
                UnifiedStreamSessionCreate(
                    source=StreamSource.TAUTULLI,
                    source_session_id="t-v1-1",
                    user_name="alice",
                    title="Movie A",
                    title_clean="movie a",
                    media_type=MediaType.MOVIE,
                    started_at=datetime.now(timezone.utc),
                )
            ]
        )
        service.ingest_sftpgo_sessions(
            [
                UnifiedStreamSessionCreate(
                    source=StreamSource.SFTPGO,
                    source_session_id="s-v1-1",
                    user_name="bob",
                    title="Episode B",
                    title_clean="episode b",
                    media_type=MediaType.EPISODE,
                    started_at=datetime.now(timezone.utc),
                )
            ]
        )
        service.mark_stale_sessions(source=StreamSource.SFTPGO)
        db.close()

        client = TestClient(app)

        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["source"] == "tautulli"

        response_sftpgo = client.get("/api/v1/sessions", params={"source": "sftpgo"})
        assert response_sftpgo.status_code == 200
        assert response_sftpgo.json() == []

        response_tautulli = client.get("/api/v1/sessions", params={"source": "tautulli"})
        assert response_tautulli.status_code == 200
        tautulli_rows = response_tautulli.json()
        assert len(tautulli_rows) == 1
        assert tautulli_rows[0]["source"] == "tautulli"
    finally:
        app.dependency_overrides.clear()


def test_active_endpoint_rejects_invalid_source_value() -> None:
    client = TestClient(app)
    response = client.get("/api/sessions/active", params={"source": "invalid-source"})
    assert response.status_code == 422
