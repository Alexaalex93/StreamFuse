from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
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

    def list_detected_users(self) -> list[dict[str, object]]:
        stmt = (
            select(
                UnifiedStreamSessionModel.user_name,
                UnifiedStreamSessionModel.source,
                func.count(UnifiedStreamSessionModel.id).label("session_count"),
            )
            .where(UnifiedStreamSessionModel.user_name.is_not(None))
            .group_by(UnifiedStreamSessionModel.user_name, UnifiedStreamSessionModel.source)
        )
        rows = self.db.execute(stmt).all()

        aggregated: dict[str, dict[str, object]] = {}
        for user_name, source, count in rows:
            cleaned_user = (str(user_name).strip() if user_name is not None else "")
            if not cleaned_user:
                continue
            item = aggregated.setdefault(
                cleaned_user,
                {"user_name": cleaned_user, "session_count": 0, "sources": set()},
            )
            item["session_count"] = int(item["session_count"]) + int(count or 0)
            item["sources"].add(str(source.value if hasattr(source, "value") else source))

        result: list[dict[str, object]] = []
        for key in sorted(aggregated.keys(), key=lambda value: value.lower()):
            value = aggregated[key]
            sources = sorted(str(source) for source in value["sources"])
            result.append(
                {
                    "user_name": str(value["user_name"]),
                    "session_count": int(value["session_count"]),
                    "sources": sources,
                }
            )
        return result

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

    def mark_missing_active_for_source(
        self,
        *,
        source: StreamSource,
        active_source_session_ids: set[str],
        ended_at: datetime,
    ) -> int:
        rows = self.list_active_by_source(source)
        changed = 0

        for row in rows:
            if row.source_session_id in active_source_session_ids:
                continue
            row.status = SessionStatus.ENDED
            row.ended_at = ended_at
            raw_payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
            raw_payload["lifecycle"] = "source_missing"
            row.raw_payload = raw_payload
            changed += 1

        if changed:
            self.db.commit()
        return changed

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

    def delete_by_user(self, user_name: str) -> int:
        """Delete ALL sessions (active and history) for *user_name*.

        Returns the number of rows deleted.
        The match is case-insensitive so that "Sheila" and "sheila" are treated
        the same way.
        """
        stmt = select(UnifiedStreamSessionModel).where(
            func.lower(UnifiedStreamSessionModel.user_name) == user_name.strip().lower()
        )
        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            self.db.delete(row)
        if rows:
            self.db.commit()
        return len(rows)

    def find_recent_ended_by_user_and_file(
        self,
        source: StreamSource,
        user_name: str,
        file_path: str,
        within_seconds: int,
    ) -> UnifiedStreamSessionModel | None:
        """Return the most-recently-ended session for *user_name* + *file_path*
        that ended within the last *within_seconds* seconds, or ``None``.

        Used to detect a "resume within the same sitting" so that a brief pause
        (e.g. the Samba connection dropped for 2 minutes, or the user paused
        and went for coffee) is merged back into the original session rather
        than creating a duplicate history entry.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=within_seconds)
        stmt = (
            select(UnifiedStreamSessionModel)
            .where(
                UnifiedStreamSessionModel.source == source,
                UnifiedStreamSessionModel.status != SessionStatus.ACTIVE,
                UnifiedStreamSessionModel.ended_at.is_not(None),
                UnifiedStreamSessionModel.ended_at >= cutoff,
                func.lower(UnifiedStreamSessionModel.user_name) == user_name.strip().lower(),
                UnifiedStreamSessionModel.file_path == file_path,
            )
            .order_by(UnifiedStreamSessionModel.ended_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_missing_mediainfo(self) -> list[UnifiedStreamSessionModel]:
        """Return sessions that have a file_path but are missing bandwidth or
        technical metadata (resolution, codec).  Used by the enrich endpoint to
        retroactively fill in data from NFO / mediainfo XML files."""
        stmt = select(UnifiedStreamSessionModel).where(
            UnifiedStreamSessionModel.file_path.is_not(None),
            UnifiedStreamSessionModel.file_path != "",
            or_(
                UnifiedStreamSessionModel.bandwidth_bps.is_(None),
                UnifiedStreamSessionModel.resolution.is_(None),
                UnifiedStreamSessionModel.video_codec.is_(None),
            ),
        )
        return list(self.db.scalars(stmt).all())

    def delete_by_ids(self, ids: list[int]) -> int:
        """Delete sessions by primary-key IDs. Returns the count deleted."""
        if not ids:
            return 0
        stmt = select(UnifiedStreamSessionModel).where(
            UnifiedStreamSessionModel.id.in_(ids)
        )
        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            self.db.delete(row)
        if rows:
            self.db.commit()
        return len(rows)

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

