from datetime import datetime, timezone

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository


class SessionService:
    def __init__(self, repository: UnifiedStreamSessionRepository) -> None:
        self.repository = repository

    def list_active_sessions(self, limit: int = 100):
        return self.repository.list_recent(limit=limit)

    def create_session(self, payload: UnifiedStreamSessionCreate):
        if payload.started_at is None:
            payload.started_at = datetime.now(timezone.utc)
        return self.repository.create(payload)

    def insert_mock_sessions(self) -> list:
        mock_items = [
            UnifiedStreamSessionCreate(
                source=StreamSource.TAUTULLI,
                source_session_id="tautulli-1001",
                status=SessionStatus.ACTIVE,
                user_name="alice",
                ip_address="192.168.1.10",
                title="Dune: Part Two",
                title_clean="dune part two",
                media_type=MediaType.MOVIE,
                file_path="/media/movies/Dune.Part.Two.mkv",
                file_name="Dune.Part.Two.mkv",
                bandwidth_bps=12000000,
                bandwidth_human="12 Mbps",
                progress_percent=42.5,
                duration_ms=9960000,
                client_name="Web",
                player_name="Plex Web",
                transcode_decision="direct play",
                resolution="4K",
                video_codec="hevc",
                audio_codec="eac3",
                raw_payload={"mock": True, "source": "tautulli"},
            ),
            UnifiedStreamSessionCreate(
                source=StreamSource.SFTPGO,
                source_session_id="sftpgo-2001",
                status=SessionStatus.ACTIVE,
                user_name="bob",
                ip_address="192.168.1.22",
                title="Ubuntu ISO",
                title_clean="ubuntu iso",
                media_type=MediaType.FILE_TRANSFER,
                file_path="/downloads/ubuntu-24.04.iso",
                file_name="ubuntu-24.04.iso",
                bandwidth_bps=25000000,
                bandwidth_human="25 Mbps",
                progress_percent=78.0,
                duration_ms=380000,
                client_name="FileZilla",
                player_name="SFTP Client",
                transcode_decision="n/a",
                resolution="n/a",
                video_codec="n/a",
                audio_codec="n/a",
                raw_payload={"mock": True, "source": "sftpgo"},
            ),
        ]

        return [self.create_session(item) for item in mock_items]
