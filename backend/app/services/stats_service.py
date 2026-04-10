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

        per_month_stmt = (
            select(
                func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at).label("period"),
                func.count().label("sessions"),
            )
            .where(*self._where(filters))
            .group_by(func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at))
            .order_by(func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at))
        )
        per_month = self.db.execute(per_month_stmt).all()

        per_year_stmt = (
            select(
                func.strftime("%Y", UnifiedStreamSessionModel.started_at).label("period"),
                func.count().label("sessions"),
            )
            .where(*self._where(filters))
            .group_by(func.strftime("%Y", UnifiedStreamSessionModel.started_at))
            .order_by(func.strftime("%Y", UnifiedStreamSessionModel.started_at))
        )
        per_year = self.db.execute(per_year_stmt).all()

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

        bandwidth_month_stmt = (
            select(
                func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at).label("period"),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
            )
            .where(*self._where(filters))
            .group_by(func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at))
            .order_by(func.strftime("%Y-%m", UnifiedStreamSessionModel.started_at))
        )
        bandwidth_month = self.db.execute(bandwidth_month_stmt).all()

        bandwidth_year_stmt = (
            select(
                func.strftime("%Y", UnifiedStreamSessionModel.started_at).label("period"),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
            )
            .where(*self._where(filters))
            .group_by(func.strftime("%Y", UnifiedStreamSessionModel.started_at))
            .order_by(func.strftime("%Y", UnifiedStreamSessionModel.started_at))
        )
        bandwidth_year = self.db.execute(bandwidth_year_stmt).all()

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

        shared_rows = self.db.execute(
            select(
                UnifiedStreamSessionModel.raw_payload,
                UnifiedStreamSessionModel.file_path,
            ).where(*self._where(filters))
        ).all()
        total_shared_bytes = sum(self._extract_shared_bytes(row.raw_payload, row.file_path) for row in shared_rows)

        return {
            "total_sessions": int(totals.total_sessions or 0),
            "active_sessions": int(totals.active_sessions or 0),
            "ended_sessions": int(totals.ended_sessions or 0),
            "stale_sessions": int(totals.stale_sessions or 0),
            "total_shared_bytes": int(total_shared_bytes),
            "total_shared_human": _format_bytes(total_shared_bytes),
            "sessions_by_day": [
                {"day": str(row.day), "sessions": int(row.sessions or 0)} for row in per_day if row.day
            ],
            "sessions_by_month": [
                {"day": str(row.period), "sessions": int(row.sessions or 0)} for row in per_month if row.period
            ],
            "sessions_by_year": [
                {"day": str(row.period), "sessions": int(row.sessions or 0)} for row in per_year if row.period
            ],
            "bandwidth_by_day": [
                {
                    "day": str(row.day),
                    "avg_bandwidth_bps": float(row.avg_bandwidth_bps or 0),
                }
                for row in bandwidth_day
                if row.day
            ],
            "bandwidth_by_month": [
                {
                    "day": str(row.period),
                    "avg_bandwidth_bps": float(row.avg_bandwidth_bps or 0),
                }
                for row in bandwidth_month
                if row.period
            ],
            "bandwidth_by_year": [
                {
                    "day": str(row.period),
                    "avg_bandwidth_bps": float(row.avg_bandwidth_bps or 0),
                }
                for row in bandwidth_year
                if row.period
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
        grouping_key = (
            func.lower(func.coalesce(UnifiedStreamSessionModel.series_title, UnifiedStreamSessionModel.title_clean, UnifiedStreamSessionModel.title, "unknown"))
            if by_series
            else func.lower(func.coalesce(UnifiedStreamSessionModel.title_clean, UnifiedStreamSessionModel.title, "unknown"))
        )
        display_title = (
            func.max(func.coalesce(UnifiedStreamSessionModel.series_title, UnifiedStreamSessionModel.title, UnifiedStreamSessionModel.title_clean, "unknown"))
            if by_series
            else func.max(func.coalesce(UnifiedStreamSessionModel.title, UnifiedStreamSessionModel.title_clean, "unknown"))
        )

        stmt = (
            select(
                grouping_key.label("group_key"),
                display_title.label("title"),
                UnifiedStreamSessionModel.media_type.label("media_type"),
                func.count().label("sessions"),
                func.count(distinct(UnifiedStreamSessionModel.user_name)).label("unique_users"),
                func.avg(UnifiedStreamSessionModel.bandwidth_bps).label("avg_bandwidth_bps"),
            )
            .where(*self._where(filters), UnifiedStreamSessionModel.media_type == media_type)
            .group_by(grouping_key, UnifiedStreamSessionModel.media_type)
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
    def _extract_shared_bytes(raw_payload: object, file_path: str | None) -> int:
        if not isinstance(raw_payload, dict):
            return 0

        file_size = raw_payload.get("file_size")
        if isinstance(file_size, (int, float)) and file_size > 0:
            return int(file_size)

        connection = raw_payload.get("connection")
        if isinstance(connection, dict):
            transfers = connection.get("active_transfers")
            if isinstance(transfers, list):
                sizes = []
                for transfer in transfers:
                    if not isinstance(transfer, dict):
                        continue
                    if str(transfer.get("operation_type") or "").lower() != "download":
                        continue
                    size = transfer.get("size")
                    if isinstance(size, (int, float)) and size > 0:
                        sizes.append(int(size))
                if sizes:
                    return max(sizes)

        bytes_sent = raw_payload.get("bytes_sent")
        if isinstance(bytes_sent, (int, float)) and bytes_sent > 0:
            return int(bytes_sent)

        if file_path and str(file_path).lower().endswith((".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".m2ts", ".mts", ".wmv", ".flv", ".webm", ".mpg", ".mpeg")):
            return 0

        return 0

    @staticmethod
    def _where(filters: StatsFilters) -> list:
        clauses = []
        if filters.date_from:
            clauses.append(UnifiedStreamSessionModel.started_at >= filters.date_from)
        if filters.date_to:
            clauses.append(UnifiedStreamSessionModel.started_at <= filters.date_to)
        return clauses


def _format_bytes(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1

    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.1f} {units[idx]}"
