from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel


@dataclass(slots=True)
class SessionQueryFilters:
    user_name: str | None = None
    source: StreamSource | None = None
    media_type: MediaType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 100


class UnifiedStreamSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, session_id: int) -> UnifiedStreamSessionModel | None:
        return self.db.scalar(select(UnifiedStreamSessionModel).where(UnifiedStreamSessionModel.id == session_id))

    def list_active_by_source(self, source: StreamSource) -> list[UnifiedStreamSessionModel]:
        stmt = select(UnifiedStreamSessionModel).where(
            UnifiedStreamSessionModel.source == source,
            UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
        )
        return list(self.db.scalars(stmt).all())

    def list_recent(self, limit: int = 100) -> list[UnifiedStreamSessionModel]:
        stmt = select(UnifiedStreamSessionModel).order_by(UnifiedStreamSessionModel.updated_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_active(self, filters: SessionQueryFilters) -> list[UnifiedStreamSessionModel]:
        clauses = [UnifiedStreamSessionModel.status == SessionStatus.ACTIVE]
        clauses.extend(self._build_filter_clauses(filters))

        stmt = (
            select(UnifiedStreamSessionModel)
            .where(and_(*clauses))
            .order_by(UnifiedStreamSessionModel.updated_at.desc())
            .limit(filters.limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_history(self, filters: SessionQueryFilters) -> list[UnifiedStreamSessionModel]:
        clauses = [UnifiedStreamSessionModel.status != SessionStatus.ACTIVE]
        clauses.extend(self._build_filter_clauses(filters))

        stmt = (
            select(UnifiedStreamSessionModel)
            .where(and_(*clauses))
            .order_by(UnifiedStreamSessionModel.updated_at.desc())
            .limit(filters.limit)
        )
        return list(self.db.scalars(stmt).all())

    def mark_active_as_stale(self, cutoff: datetime, source: StreamSource | None = None) -> int:
        clauses = [
            UnifiedStreamSessionModel.status == SessionStatus.ACTIVE,
            UnifiedStreamSessionModel.updated_at < cutoff,
        ]
        if source is not None:
            clauses.append(UnifiedStreamSessionModel.source == source)

        rows = list(self.db.scalars(select(UnifiedStreamSessionModel).where(and_(*clauses))).all())

        for row in rows:
            row.status = SessionStatus.ENDED
            row.ended_at = cutoff
            raw_payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
            raw_payload["lifecycle"] = "stale"
            row.raw_payload = raw_payload

        if rows:
            self.db.commit()
        return len(rows)

    def create(self, payload: UnifiedStreamSessionCreate) -> UnifiedStreamSessionModel:
        existing = self.db.scalar(
            select(UnifiedStreamSessionModel).where(
                UnifiedStreamSessionModel.source == payload.source,
                UnifiedStreamSessionModel.source_session_id == payload.source_session_id,
            )
        )

        if existing:
            for key, value in payload.model_dump().items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        model = UnifiedStreamSessionModel(**payload.model_dump())
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    @staticmethod
    def _build_filter_clauses(filters: SessionQueryFilters) -> list:
        clauses = []
        if filters.user_name:
            clauses.append(UnifiedStreamSessionModel.user_name == filters.user_name)
        if filters.source:
            clauses.append(UnifiedStreamSessionModel.source == filters.source)
        if filters.media_type:
            clauses.append(UnifiedStreamSessionModel.media_type == filters.media_type)
        if filters.date_from:
            clauses.append(UnifiedStreamSessionModel.started_at >= filters.date_from)
        if filters.date_to:
            clauses.append(UnifiedStreamSessionModel.started_at <= filters.date_to)
        return clauses
