from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import StreamSource
from app.persistence.db import Base


class IngestionLogModel(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[StreamSource] = mapped_column(
        Enum(StreamSource, name="stream_source", native_enum=False),
        index=True,
    )
    operation: Mapped[str] = mapped_column(String(64), default="sync")
    records_received: Mapped[int] = mapped_column(default=0)
    records_written: Mapped[int] = mapped_column(default=0)
    success: Mapped[bool] = mapped_column(default=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
