from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.main import app
from app.persistence.db import Base
from app.persistence.models import unified_stream_session  # noqa: F401
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.unified_session_service import UnifiedSessionService


def _seed_data(session_local):
    db = session_local()
    service = UnifiedSessionService(UnifiedStreamSessionRepository(db))
    now = datetime.now(timezone.utc)

    service.ingest_tautulli_sessions(
        [
            UnifiedStreamSessionCreate(
                source=StreamSource.TAUTULLI,
                source_session_id="t1",
                status=SessionStatus.ACTIVE,
                user_name="alice",
                title="Dune Part Two",
                title_clean="dune part two",
                media_type=MediaType.MOVIE,
                bandwidth_bps=12_000_000,
                started_at=now - timedelta(days=2),
            ),
            UnifiedStreamSessionCreate(
                source=StreamSource.TAUTULLI,
                source_session_id="t2",
                status=SessionStatus.ENDED,
                user_name="alice",
                title="Arrival",
                title_clean="arrival",
                media_type=MediaType.MOVIE,
                bandwidth_bps=8_000_000,
                started_at=now - timedelta(days=1),
                ended_at=now - timedelta(days=1, hours=-1),
            ),
        ]
    )

    service.ingest_sftpgo_sessions(
        [
            UnifiedStreamSessionCreate(
                source=StreamSource.SFTPGO,
                source_session_id="s1",
                status=SessionStatus.ACTIVE,
                user_name="bob",
                title="The Expanse S02E05",
                title_clean="the expanse s02e05",
                media_type=MediaType.EPISODE,
                series_title="The Expanse",
                bandwidth_bps=5_000_000,
                started_at=now - timedelta(days=1),
            ),
            UnifiedStreamSessionCreate(
                source=StreamSource.SFTPGO,
                source_session_id="s2",
                status=SessionStatus.ENDED,
                user_name="carol",
                title="The Expanse S02E06",
                title_clean="the expanse s02e06",
                media_type=MediaType.EPISODE,
                series_title="The Expanse",
                bandwidth_bps=6_000_000,
                started_at=now,
                ended_at=now,
                raw_payload={"lifecycle": "stale"},
            ),
        ]
    )
    db.close()


def test_stats_endpoints_for_dashboard() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    _seed_data(SessionLocal)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        overview = client.get("/api/stats/overview")
        users = client.get("/api/stats/users")
        media = client.get("/api/stats/media")

        assert overview.status_code == 200
        assert users.status_code == 200
        assert media.status_code == 200

        overview_json = overview.json()
        users_json = users.json()
        media_json = media.json()

        assert overview_json["total_sessions"] == 4
        assert overview_json["active_sessions"] == 2
        assert overview_json["ended_sessions"] == 2
        assert overview_json["stale_sessions"] >= 1
        assert len(overview_json["sessions_by_day"]) >= 2
        assert len(overview_json["sessions_by_month"]) >= 1
        assert len(overview_json["sessions_by_year"]) >= 1
        assert len(overview_json["bandwidth_by_day"]) >= 2
        assert len(overview_json["bandwidth_by_month"]) >= 1
        assert len(overview_json["bandwidth_by_year"]) >= 1
        assert overview_json["total_shared_bytes"] >= 0
        assert isinstance(overview_json["total_shared_human"], str)
        assert {item["source"] for item in overview_json["source_distribution"]} == {"tautulli", "sftpgo"}
        assert len(overview_json["active_by_source"]) >= 1

        assert users_json["items"][0]["user_name"] == "alice"
        assert users_json["items"][0]["sessions"] >= 2

        assert len(media_json["top_movies"]) >= 1
        assert len(media_json["top_series"]) >= 1
    finally:
        app.dependency_overrides.clear()


def test_stats_filters_by_date_range() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    _seed_data(SessionLocal)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        today = datetime.now(timezone.utc).date().isoformat()
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()

        filtered = client.get(
            "/api/stats/overview",
            params={
                "date_from": f"{today}T00:00:00Z",
                "date_to": f"{tomorrow}T00:00:00Z",
            },
        )

        assert filtered.status_code == 200
        data = filtered.json()
        assert data["total_sessions"] >= 1
        assert data["total_sessions"] < 4
    finally:
        app.dependency_overrides.clear()

