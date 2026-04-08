from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, desc, distinct, func, select
from sqlalchemy.orm import Session

from app.domain.enums import MediaType, SessionStatus
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel


@dataclass(slots=True)
class StatsFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_overview(self, filters: StatsFilters) -> dict:
        totals_stmt = select(
            func.count().label("total_sessions"),
            func.sum(case((UnifiedStreamSessionModel.status == SessionStatus.ACTIVE, 1), else_=0)).label(
                "active_sessions"
            ),
            func.sum(case((UnifiedStreamSessionModel.status == SessionStatus.ENDED, 1), else_=0)).label(
                "ended_sessions"
            ),
            func.sum(
                case(
                    (
                        UnifiedStreamSessionModel.raw_payload["lifecycle"].as_string() == "stale",
                        1,
                    ),
                    else_=0,
                )
            ).label("stale_sessions"),
        ).where(*self._where(filters))

        totals = self.db.execute(totals_stmt).one()

        per_day_stmt = (
            select(
                func.date(UnifiedStreamSessionModel.started_at).label("day"),
                func.count().label("sessions"),
            )
            .where(*self._where(filters))
            .group_by(func.date(UnifiedStreamSessionModel.started_at))
            .order_by(func.date(UnifiedStreamSessionModel.started_at))
        )
        per_day = self.db.execute(per_day_stmt).all()

        bandwidth_day_stmt = (
            select(
                func.date(UnifiedStreamSessionModel.started_at).label("day"),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
            )
            .where(*self._where(filters))
            .group_by(func.date(UnifiedStreamSessionModel.started_at))
            .order_by(func.date(UnifiedStreamSessionModel.started_at))
        )
        bandwidth_day = self.db.execute(bandwidth_day_stmt).all()

        source_dist_stmt = (
            select(
                UnifiedStreamSessionModel.source.label("source"),
                func.count().label("sessions"),
            )
            .where(*self._where(filters))
            .group_by(UnifiedStreamSessionModel.source)
            .order_by(desc("sessions"))
        )
        source_distribution = self.db.execute(source_dist_stmt).all()

        active_source_stmt = (
            select(
                UnifiedStreamSessionModel.source.label("source"),
                func.count().label("sessions"),
            )
            .where(*self._where(filters), UnifiedStreamSessionModel.status == SessionStatus.ACTIVE)
            .group_by(UnifiedStreamSessionModel.source)
            .order_by(desc("sessions"))
        )
        active_by_source = self.db.execute(active_source_stmt).all()

        return {
            "total_sessions": int(totals.total_sessions or 0),
            "active_sessions": int(totals.active_sessions or 0),
            "ended_sessions": int(totals.ended_sessions or 0),
            "stale_sessions": int(totals.stale_sessions or 0),
            "sessions_by_day": [
                {"day": str(row.day), "sessions": int(row.sessions or 0)} for row in per_day if row.day
            ],
            "bandwidth_by_day": [
                {
                    "day": str(row.day),
                    "avg_bandwidth_bps": float(row.avg_bandwidth_bps or 0),
                }
                for row in bandwidth_day
                if row.day
            ],
            "source_distribution": [
                {"source": row.source.value if row.source else "unknown", "sessions": int(row.sessions or 0)}
                for row in source_distribution
            ],
            "active_by_source": [
                {"source": row.source.value if row.source else "unknown", "sessions": int(row.sessions or 0)}
                for row in active_by_source
            ],
        }

    def get_top_users(self, filters: StatsFilters, limit: int = 10) -> list[dict]:
        stmt = (
            select(
                UnifiedStreamSessionModel.user_name.label("user_name"),
                func.count().label("sessions"),
                func.sum(case((UnifiedStreamSessionModel.status == SessionStatus.ACTIVE, 1), else_=0)).label(
                    "active_sessions"
                ),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
                func.max(UnifiedStreamSessionModel.updated_at).label("last_seen_at"),
            )
            .where(*self._where(filters))
            .group_by(UnifiedStreamSessionModel.user_name)
            .order_by(desc("sessions"), desc("last_seen_at"))
            .limit(limit)
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "user_name": row.user_name or "unknown",
                "sessions": int(row.sessions or 0),
                "active_sessions": int(row.active_sessions or 0),
                "avg_bandwidth_bps": float(row.avg_bandwidth_bps) if row.avg_bandwidth_bps is not None else None,
                "last_seen_at": row.last_seen_at,
            }
            for row in rows
        ]

    def get_top_media(self, filters: StatsFilters, limit: int = 10) -> dict:
        movies = self._top_media_by_type(MediaType.MOVIE, filters, limit)
        series = self._top_media_by_type(MediaType.EPISODE, filters, limit, by_series=True)
        return {
            "top_movies": movies,
            "top_series": series,
        }

    def _top_media_by_type(
        self,
        media_type: MediaType,
        filters: StatsFilters,
        limit: int,
        by_series: bool = False,
    ) -> list[dict]:
        title_expr = UnifiedStreamSessionModel.series_title if by_series else UnifiedStreamSessionModel.title

        stmt = (
            select(
                func.coalesce(title_expr, UnifiedStreamSessionModel.title_clean, "unknown").label("title"),
                UnifiedStreamSessionModel.media_type.label("media_type"),
                func.count().label("sessions"),
                func.count(distinct(UnifiedStreamSessionModel.user_name)).label("unique_users"),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
            )
            .where(*self._where(filters), UnifiedStreamSessionModel.media_type == media_type)
            .group_by(
                func.coalesce(title_expr, UnifiedStreamSessionModel.title_clean, "unknown"),
                UnifiedStreamSessionModel.media_type,
            )
            .order_by(desc("sessions"))
            .limit(limit)
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "title": row.title,
                "media_type": row.media_type.value if row.media_type else "unknown",
                "sessions": int(row.sessions or 0),
                "unique_users": int(row.unique_users or 0),
                "avg_bandwidth_bps": float(row.avg_bandwidth_bps) if row.avg_bandwidth_bps is not None else None,
            }
            for row in rows
        ]

    @staticmethod
    def _where(filters: StatsFilters) -> list:
        clauses = []
        if filters.date_from:
            clauses.append(UnifiedStreamSessionModel.started_at >= filters.date_from)
        if filters.date_to:
            clauses.append(UnifiedStreamSessionModel.started_at <= filters.date_to)
        return clauses
