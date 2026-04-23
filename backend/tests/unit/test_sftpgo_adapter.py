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
                    # > 50 MB so _looks_like_download treats this as real playback
                    "bytes_sent": 60_000_000,
                    # 120 s ago so _mark_stale_sessions marks ENDED rather than
                    # silently deleting it as a sub-60 s library-scan pre-buffer
                    "start_time": int(datetime.now(timezone.utc).timestamp()) - 120,
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
                # > 50 MB so _looks_like_download passes (real playback, not browse pre-buffer)
                "bytes_sent": 55_000_000,
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
                    # > 50 MB so both connections pass _looks_like_download
                    "bytes_sent": 60_000_000,
                    "info": 'DL: "/media/movies/Arrival.2016.mkv"',
                },
                {
                    "connection_id": "broken-1",
                    "username": "bob",
                    "ip_address": "192.168.1.21",
                    "file_path": "/media/movies/Broken.mkv",
                    "bytes_sent": 60_000_000,
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

def test_sftpgo_cleans_invalid_active_sessions() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))

        service.create_session(
            build_sftpgo_session_payload(
                source_session_id="legacy-invalid-1",
                connection={
                    "username": "legacy",
                    "ip_address": "10.0.0.1",
                    "protocol": "ftp",
                },
                related_logs=[],
                status=SessionStatus.ACTIVE,
                bandwidth_bps=None,
                poster_path=None,
                media_info=None,
            )
        )

        sync = SFTPGoSyncService(
            client=SFTPGoClient(_EphemeralProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        result = asyncio.run(sync.poll_once(log_limit=10))

        cleaned = db.scalar(
            select(UnifiedStreamSessionModel).where(
                UnifiedStreamSessionModel.source_session_id == "legacy-invalid-1"
            )
        )

        assert result["cleaned_invalid"] >= 1
        assert cleaned is None
    finally:
        db.close()


class _NoopProvider(SFTPGoProvider):
    async def fetch_active_connections(self):
        return []

    async def fetch_transfer_logs(self, limit: int = 200):
        return []


def test_sftpgo_collapses_duplicate_active_rows_from_previous_runs() -> None:
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))

        base_connection = {
            "username": "marlene",
            "ip_address": "79.117.96.46",
            "protocol": "ftp",
            "file_path": "/peliculas/2 Fast 2 Furious (2003) {tmdb-584}/2 Fast 2 Furious (2003) {tmdb-584}.mkv",
            "streamfuse_logical_key": "marlene|79.117.96.46|/peliculas/2 fast 2 furious (2003) {tmdb-584}/2 fast 2 furious (2003) {tmdb-584}.mkv",
        }

        payload_a = build_sftpgo_session_payload(
            source_session_id="dup-a",
            connection=base_connection,
            related_logs=[],
            status=SessionStatus.ACTIVE,
            bandwidth_bps=1_000_000,
            poster_path=None,
            media_info=None,
        )

        payload_b = build_sftpgo_session_payload(
            source_session_id="dup-b",
            connection={**base_connection, "bytes_sent": 9_999_999},
            related_logs=[],
            status=SessionStatus.ACTIVE,
            bandwidth_bps=2_000_000,
            poster_path=None,
            media_info=None,
        )

        service.create_session(payload_a)
        service.create_session(payload_b)

        sync = SFTPGoSyncService(
            client=SFTPGoClient(_NoopProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        result = asyncio.run(sync.poll_once(log_limit=10))

        rows = list(
            db.scalars(
                select(UnifiedStreamSessionModel).where(
                    UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                    UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
                )
            ).all()
        )

        assert result["cleaned_duplicate_active"] == 1
        assert len(rows) == 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# NAT-timeout reconnection aggregation
# ---------------------------------------------------------------------------

_HP_PATH = (
    "/multimedia/peliculas/Harry Potter and the Philosopher's Stone (2001) {tmdb-671}"
    "/Harry Potter and the Philosopher's Stone (2001) {tmdb-671}.mkv"
)


class _NATReconnectProvider(SFTPGoProvider):
    """Simulates a user whose router drops idle FTP connections every ~120 s.

    The active connection currently in progress has only sent 5 MB (just
    reconnected).  Eight previous segments are in the completed-log file, each
    between 6 MB and 17 MB — all individually below the 50 MB threshold.
    The cumulative total is ≈ 92 MB, which IS above the threshold.
    """

    _SEGMENTS = [
        16_809_984,   # FTP_0_899
        13_303_808,   # FTP_0_900
        11_698_176,   # FTP_0_901
         8_585_216,   # FTP_0_902
         6_062_080,   # FTP_0_903
        15_138_816,   # FTP_0_904
        10_256_384,   # FTP_0_905
        10_240_000,   # FTP_0_906 (rounded up from 2.5 MB to ensure total > 50 MB)
    ]  # total ≈ 92 MB

    async def fetch_active_connections(self):
        import time
        return [
            {
                "connection_id": "FTP_0_909",   # new reconnect, few bytes so far
                "username": "Rubi",
                "protocol": "FTP",
                "remote_address": "83.36.144.43:57374",
                "active_transfers": [
                    {
                        "operation_type": "download",
                        "virtual_path": _HP_PATH,
                        "size": 5_242_880,          # 5 MB — well below 50 MB
                        "start_time": int(time.time()) - 15,
                    }
                ],
            }
        ]

    async def fetch_transfer_logs(self, limit: int = 200):
        import time
        now = int(time.time())
        entries = []
        for i, size in enumerate(self._SEGMENTS):
            # Each segment completed ~2 min apart, all within last 30 min
            ts = now - (len(self._SEGMENTS) - i) * 125
            entries.append({
                "sender": "Download",
                "ts": ts,
                "username": "Rubi",
                "file_path": _HP_PATH,
                "connection_id": f"FTP_0_{899 + i}",
                "size_bytes": size,
                "elapsed_ms": 120_500,
                "protocol": "FTP",
            })
        return entries


def test_sftpgo_nat_reconnect_aggregation_creates_session() -> None:
    """Multiple small FTP segments (each < 50 MB) from a user with NAT timeouts
    must be aggregated into one session when their cumulative total ≥ 50 MB."""
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(_NATReconnectProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
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

        assert result["active_imported"] >= 1, (
            "Expected at least one session to be imported via NAT-reconnect "
            f"cumulative bytes aggregation; got {result}"
        )
        assert len(rows) == 1
        row = rows[0]
        assert row.user_name and row.user_name.lower() == "rubi"
        assert row.file_path and "Harry Potter" in row.file_path
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Log-only session creation (parallel offline download, no active connection)
# ---------------------------------------------------------------------------

_PRIMATE_PATH = (
    "/multimedia/peliculas/Primate (2026) {tmdb-1315303}"
    "/Primate (2026) {tmdb-1315303}.mkv"
)


class _ParallelDownloadProvider(SFTPGoProvider):
    """Simulates Antonio's overnight parallel FTP download.

    Four simultaneous connections each making many range requests.  All
    complete in seconds at full network speed — no connection is ever active
    when StreamFuse polls.  The total transferred data is well above 50 MB.
    """

    async def fetch_active_connections(self):
        # Download already finished — no active connections at poll time.
        return []

    async def fetch_transfer_logs(self, limit: int = 200):
        import time
        now = int(time.time())
        entries = []
        # 4 parallel connections × 10 RETR operations each = 40 segments
        # Each segment ≈ 20 MB at ~40 MB/s (elapsed ≈ 500 ms).
        # Total ≈ 800 MB — clearly a full movie download.
        for conn_idx in range(4):
            conn_id = f"FTP_0_{800 + conn_idx}"
            for seg_idx in range(10):
                entries.append({
                    "sender": "Download",
                    "ts": now - 300 + conn_idx + seg_idx,  # within last 5 min
                    "username": "Antonio",
                    "file_path": _PRIMATE_PATH,
                    "connection_id": conn_id,
                    "size_bytes": 20_000_000,   # 20 MB per segment
                    "elapsed_ms": 500,           # 500 ms per segment
                    "protocol": "FTP",
                })
        return entries[:limit]


def test_sftpgo_log_only_parallel_download_creates_history_entry() -> None:
    """A parallel offline download (no active connection ever seen by StreamFuse)
    must be captured as a completed history entry via the log-only import path."""
    session_local = _setup_db()
    settings = _make_settings()

    db = session_local()
    try:
        service = SessionService(UnifiedStreamSessionRepository(db))
        sync = SFTPGoSyncService(
            client=SFTPGoClient(_ParallelDownloadProvider()),
            session_service=service,
            poster_resolver=PosterResolver(settings),
            stale_seconds=300,
        )

        result = asyncio.run(sync.poll_once(log_limit=200))

        rows = list(
            db.scalars(
                select(UnifiedStreamSessionModel).where(
                    UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
                    UnifiedStreamSessionModel.status == SessionStatus.ENDED,
                )
            ).all()
        )

        assert result["log_only_imported"] == 1, (
            "Expected one log-only ENDED session for Antonio's parallel download; "
            f"got {result}"
        )
        assert len(rows) == 1
        row = rows[0]
        assert row.user_name and row.user_name.lower() == "antonio"
        assert row.file_path and "Primate" in row.file_path
        assert row.status == SessionStatus.ENDED

        # Second poll must NOT duplicate the entry (deduplication via DB check).
        result2 = asyncio.run(sync.poll_once(log_limit=200))
        assert result2["log_only_imported"] == 0, (
            f"Second poll must not duplicate the history entry; got {result2}"
        )
    finally:
        db.close()
