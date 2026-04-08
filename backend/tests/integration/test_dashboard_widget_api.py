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


def test_dashboard_widget_compact_response() -> None:
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
                    source_session_id="t-w-1",
                    user_name="alice",
                    title="Dune Part Two",
                    title_clean="dune part two",
                    media_type=MediaType.MOVIE,
                    bandwidth_bps=12_000_000,
                    started_at=datetime.now(timezone.utc),
                ),
                UnifiedStreamSessionCreate(
                    source=StreamSource.TAUTULLI,
                    source_session_id="t-w-2",
                    user_name="john",
                    title="Fallout",
                    title_clean="fallout",
                    media_type=MediaType.EPISODE,
                    bandwidth_bps=6_000_000,
                    started_at=datetime.now(timezone.utc),
                ),
            ]
        )

        service.ingest_sftpgo_sessions(
            [
                UnifiedStreamSessionCreate(
                    source=StreamSource.SFTPGO,
                    source_session_id="s-w-1",
                    user_name="bob",
                    title="Ubuntu ISO",
                    title_clean="ubuntu iso",
                    media_type=MediaType.FILE_TRANSFER,
                    bandwidth_bps=25_000_000,
                    started_at=datetime.now(timezone.utc),
                )
            ]
        )
        db.close()

        client = TestClient(app)
        response = client.get("/api/dashboard/widget", params={"limit": 2})

        assert response.status_code == 200
        payload = response.json()

        assert payload["summary"]["active_sessions"] == 3
        assert payload["summary"]["tautulli_sessions"] == 2
        assert payload["summary"]["sftpgo_sessions"] == 1
        assert payload["summary"]["total_bandwidth_bps"] == 43_000_000

        assert len(payload["sessions"]) == 2
        assert payload["hidden_count"] == 1
        assert payload["sessions"][0]["poster_url"].startswith("/api/v1/posters/")
    finally:
        app.dependency_overrides.clear()