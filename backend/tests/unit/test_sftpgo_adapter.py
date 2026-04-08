import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.sftpgo.client import SFTPGoClient, SFTPGoMockProvider, SFTPGoProvider
from app.adapters.sftpgo.log_parser import parse_transfer_log_lines
from app.adapters.sftpgo.mapper import build_sftpgo_session_payload
from app.core.config import Settings
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.mediainfo_parser import MediaInfoSummary
from app.persistence.db import Base
from app.persistence.models import unified_stream_session  # noqa: F401
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.persistence.repositories.unified_stream_session_repository import (
    UnifiedStreamSessionRepository,
)
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService
from app.services.sftpgo_sync_service import SFTPGoSyncService


class _EphemeralProvider(SFTPGoProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def fetch_active_connections(self):
        self.calls += 1
        if self.calls == 1:
            return [
                {
                    "connection_id": "stale-1",
                    "username": "stale_user",
                    "ip_address": "192.168.1.90",
                    "file_path": "/media/movies/Arrival.2016.mkv",
                    "bytes_sent": 1000,
                    "start_time": int(datetime.now(timezone.utc).timestamp()) - 60,
                    "info": 'DL: "/media/movies/Arrival.2016.mkv"',
                }
            ]
        return []

    async def fetch_transfer_logs(self, limit: int = 200):
        return []


class _DuplicateDownloadProvider(SFTPGoProvider):
    async def fetch_active_connections(self):
        return [
            {
                "connection_id": "c-1",
                "username": "marlene",
                "remote_address": "79.117.96.46:54967",
                "protocol": "ftp",
                "bytes_sent": 13_300_000,
                "last_activity": 1710000000,
                "info": 'DL: "/multimedia/peliculas/2 Fast 2 Furious (2003) {tmdb-584}/2 Fast 2 Furious (2003) {tmdb-584}.mkv"',
            },
            {
                "connection_id": "c-2",
                "username": "marlene",
                "remote_address": "79.117.96.46:54969",
                "protocol": "ftp",
                "bytes_sent": 45_700_000,
                "last_activity": 1710000010,
                "info": 'DL: "/multimedia/peliculas/2 Fast 2 Furious (2003) {tmdb-584}/2 Fast 2 Furious (2003) {tmdb-584}.mkv"',
            },
            {
                "connection_id": "c-3",
                "username": "alex",
                "remote_address": "79.117.96.46:54930",
                "protocol": "ftp",
                "bytes_sent": 0,
                "last_activity": 1710000010,
                "info": "Client: Unknown",
            },
        ]

    async def fetch_transfer_logs(self, limit: int = 200):
        return [
            {
                "connection_id": "c-1",
                "event": "download",
                "username": "marlene",
                "remote_addr": "79.117.96.46:54967",
                "file_path": "/multimedia/peliculas/2 Fast 2 Furious (2003) {tmdb-584}/2 Fast 2 Furious (2003) {tmdb-584}.mkv",
                "bytes_sent": 13_300_000,
            },
            {
                "connection_id": "c-2",
                "event": "download",
                "username": "marlene",
                "remote_addr": "79.117.96.46:54969",
                "file_path": "/multimedia/peliculas/2 Fast 2 Furious (2003) {tmdb-584}/2 Fast 2 Furious (2003) {tmdb-584}.mkv",
                "bytes_sent": 45_700_000,
            },
            {
                "connection_id": "c-3",
                "event": "login",
                "username": "alex",
                "remote_addr": "79.117.96.46:54930",
            },
        ]


def _make_settings() -> Settings:
    fixtures_root = (Path(__file__).resolve().parents[1] / "fixtures").resolve()
    placeholder = fixtures_root / "posters" / "placeholder.svg"
    return Settings(
        poster_placeholder_path=str(placeholder),
        poster_allowed_roots=str(fixtures_root),
    )


def _setup_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return session_local


def test_parse_transfer_log_lines_skips_invalid_json() -> None:
    rows = parse_transfer_log_lines(
        [
            '{"connection_id":"c1","bytes_sent":10}',
            "not-json",
            '{"connection_id":"c2","bytes_sent":20}',
        ]
    )

    assert len(rows) == 2
    assert rows[0]["connection_id"] == "c1"
    assert rows[1]["connection_id"] == "c2"


def test_sftpgo_sync_imports_mock_as_unified_sessions() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(SFTPGoMockProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        result = asyncio.run(sync.poll_once(log_limit=200))
        rows = list(db.scalars(select(UnifiedStreamSessionModel)).all())

        assert result["active_imported"] >= 1
        assert len(rows) >= 1
        assert all(row.source.value == "sftpgo" for row in rows)
        assert all(row.progress_percent is None for row in rows)
        assert all(row.raw_payload is not None for row in rows)
    finally:
        db.close()


def test_sftpgo_bandwidth_estimation_on_second_poll() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(SFTPGoMockProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        asyncio.run(sync.poll_once(log_limit=200))
        asyncio.run(asyncio.sleep(0.05))
        asyncio.run(sync.poll_once(log_limit=200))

        row = db.scalar(
            select(UnifiedStreamSessionModel).where(
                UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
            )
        )
        assert row is not None
        assert row.bandwidth_bps is not None
        assert row.bandwidth_bps > 0
    finally:
        db.close()


def test_sftpgo_detects_stale_session_and_marks_ended() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(_EphemeralProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=0,
        )

        asyncio.run(sync.poll_once(log_limit=10))
        asyncio.run(asyncio.sleep(0.02))
        result = asyncio.run(sync.poll_once(log_limit=10))

        row = db.scalar(
            select(UnifiedStreamSessionModel).where(
                UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                UnifiedStreamSessionModel.status == SessionStatus.ENDED,
            )
        )

        assert result["stale_marked"] >= 1
        assert row is not None
        assert row.status == SessionStatus.ENDED
    finally:
        db.close()


def test_sftpgo_poll_once_counts_errors_and_continues(monkeypatch, caplog) -> None:
    class _Provider(SFTPGoProvider):
        async def fetch_active_connections(self):
            return [
                {
                    "connection_id": "ok-1",
                    "username": "alice",
                    "ip_address": "192.168.1.20",
                    "file_path": "/media/movies/Arrival.2016.mkv",
                    "bytes_sent": 10,
                    "info": 'DL: "/media/movies/Arrival.2016.mkv"',
                },
                {
                    "connection_id": "broken-1",
                    "username": "bob",
                    "ip_address": "192.168.1.21",
                    "file_path": "/media/movies/Broken.mkv",
                    "bytes_sent": 20,
                    "info": 'DL: "/media/movies/Broken.mkv"',
                },
            ]

        async def fetch_transfer_logs(self, limit: int = 200):
            return []

    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(_Provider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        real_builder = build_sftpgo_session_payload

        def _faulty_builder(
            *,
            source_session_id,
            connection,
            related_logs,
            status,
            bandwidth_bps,
            poster_path,
            media_info=None,
            ended_at=None,
        ):
            if connection.get("username") == "bob":
                raise ValueError("bad connection")
            return real_builder(
                source_session_id=source_session_id,
                connection=connection,
                related_logs=related_logs,
                status=status,
                bandwidth_bps=bandwidth_bps,
                poster_path=poster_path,
                media_info=media_info,
                ended_at=ended_at,
            )

        monkeypatch.setattr(
            "app.services.sftpgo_sync_service.build_sftpgo_session_payload",
            _faulty_builder,
        )

        with caplog.at_level("ERROR"):
            result = asyncio.run(sync.poll_once(log_limit=10))

        rows = list(db.scalars(select(UnifiedStreamSessionModel)).all())

        assert result["active_imported"] == 1
        assert result["errors"] == 1
        assert len(rows) == 1
        assert "Failed to map/store SFTPGo payload" in caplog.text
    finally:
        db.close()


def test_sftpgo_applies_mediainfo_fields(monkeypatch) -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(SFTPGoMockProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        monkeypatch.setattr(
            "app.services.sftpgo_sync_service.parse_mediainfo_for_media",
            lambda _: MediaInfoSummary(
                title="Temporada de asesinatos",
                duration_ms=3_492_960,
                overall_bitrate_bps=7_682_012,
                video_bitrate_bps=6_249_140,
                resolution="1920x960",
                video_codec="HEVC",
                audio_codec="E-AC-3",
                frame_rate=23.976,
                audio_channels=6,
            ),
        )

        asyncio.run(sync.poll_once(log_limit=200))

        row = db.scalar(
            select(UnifiedStreamSessionModel).where(
                UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
            )
        )

        assert row is not None
        assert row.resolution == "1920x960"
        assert row.video_codec == "HEVC"
        assert row.audio_codec == "E-AC-3"
        assert row.transcode_decision == "direct play"
        assert row.duration_ms == 3_492_960
        assert isinstance(row.raw_payload, dict)
        assert row.raw_payload.get("media_info", {}).get("video_bitrate_bps") == 6_249_140
    finally:
        db.close()


def test_sftpgo_merges_same_download_across_ports() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(_DuplicateDownloadProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
            path_mappings=["/multimedia/peliculas:/peliculas"],
        )

        result = asyncio.run(sync.poll_once(log_limit=200))

        rows = list(
            db.scalars(
                select(UnifiedStreamSessionModel).where(
                    UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                    UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
                )
            ).all()
        )

        assert result["active_imported"] == 1
        assert len(rows) == 1
        assert rows[0].ip_address == "79.117.96.46"
        assert "/peliculas/2 Fast 2 Furious" in (rows[0].file_path or "")
    finally:
        db.close()
