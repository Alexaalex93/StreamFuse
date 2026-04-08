from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import MediaType
from app.persistence.db import Base


class MediaItemModel(Base):
    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    title_clean: Mapped[str] = mapped_column(String(512), index=True)
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
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
