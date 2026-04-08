from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Enum, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.persistence.db import Base


class UnifiedStreamSessionModel(Base):
    __tablename__ = "unified_stream_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[StreamSource] = mapped_column(
        Enum(StreamSource, name="stream_source", native_enum=False),
        index=True,
    )
    source_session_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", native_enum=False),
        default=SessionStatus.ACTIVE,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    media_item_id: Mapped[int | None] = mapped_column(ForeignKey("media_items.id"), nullable=True)

    user_name: Mapped[str] = mapped_column(String(128), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title_clean: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", native_enum=False),
        default=MediaType.OTHER,
        index=True,
    )
    series_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    bandwidth_bps: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bandwidth_human: Mapped[str | None] = mapped_column(String(64), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    progress_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    client_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    player_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transcode_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    video_codec: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String(64), nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("UserModel")
    media_item = relationship("MediaItemModel")


Index(
    "ix_unified_source_session",
    UnifiedStreamSessionModel.source,
    UnifiedStreamSessionModel.source_session_id,
    unique=True,
)
