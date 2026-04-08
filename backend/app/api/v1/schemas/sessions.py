from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MediaType, SessionStatus, StreamSource


class UnifiedStreamSessionCreate(BaseModel):
    source: StreamSource
    source_session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    user_name: str
    ip_address: str | None = None
    title: str | None = None
    title_clean: str | None = None
    media_type: MediaType = MediaType.OTHER
    series_title: str | None = None
    season_number: int | None = None
    episode_number: int | None = None
    file_path: str | None = None
    file_name: str | None = None
    poster_path: str | None = None
    bandwidth_bps: int | None = None
    bandwidth_human: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    duration_ms: int | None = None
    client_name: str | None = None
    player_name: str | None = None
    transcode_decision: str | None = None
    resolution: str | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    raw_payload: dict | None = None


class UnifiedStreamSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: StreamSource
    source_session_id: str
    status: SessionStatus
    user_name: str
    ip_address: str | None
    title: str | None
    title_clean: str | None
    media_type: MediaType
    series_title: str | None
    season_number: int | None
    episode_number: int | None
    file_path: str | None
    file_name: str | None
    poster_path: str | None
    bandwidth_bps: int | None
    bandwidth_human: str | None
    started_at: datetime
    ended_at: datetime | None
    updated_at: datetime
    progress_percent: float | None
    duration_ms: int | None
    client_name: str | None
    player_name: str | None
    transcode_decision: str | None
    resolution: str | None
    video_codec: str | None
    audio_codec: str | None
    raw_payload: dict | None
