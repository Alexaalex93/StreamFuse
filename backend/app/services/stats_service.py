from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import case, desc, distinct, func, select
from sqlalchemy.orm import Session

from app.domain.enums import MediaType, SessionStatus
from app.persistence.models.app_setting import AppSettingModel
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.services.user_alias_service import UserAliasService


@dataclass(slots=True)
class StatsFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.alias_service = UserAliasService(db)
        self.timezone = self._load_timezone()

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
                "user_name": self.alias_service.resolve(row.user_name),
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

    def get_user_insights(self, filters: StatsFilters, limit: int = 50) -> dict:
        stmt = select(
            UnifiedStreamSessionModel.user_name,
            UnifiedStreamSessionModel.media_type,
            UnifiedStreamSessionModel.title,
            UnifiedStreamSessionModel.title_clean,
            UnifiedStreamSessionModel.series_title,
            UnifiedStreamSessionModel.file_path,
            UnifiedStreamSessionModel.started_at,
            UnifiedStreamSessionModel.ended_at,
            UnifiedStreamSessionModel.duration_ms,
            UnifiedStreamSessionModel.updated_at,
        ).where(*self._where(filters))

        rows = self.db.execute(stmt).all()

        per_user: dict[str, dict] = {}
        hour_counts = [0] * 24

        for row in rows:
            user_name = self.alias_service.resolve(row.user_name)
            bucket = per_user.setdefault(
                user_name,
                {
                    "user_name": user_name,
                    "total_sessions": 0,
                    "movie_sessions": 0,
                    "episode_sessions": 0,
                    "total_watch_ms": 0,
                    "movie_watch_ms": 0,
                    "episode_watch_ms": 0,
                    "_unique_titles_monthly": set(),
                    "_unique_movies_monthly": set(),
                    "_unique_series_monthly": set(),
                    "last_seen_at": None,
                },
            )

            bucket["total_sessions"] += 1
            watch_ms = self._resolve_watch_ms(row.duration_ms, row.started_at, row.ended_at)
            bucket["total_watch_ms"] += watch_ms

            month_key = self._month_key(row.started_at)
            media_key = self._media_key(row.title_clean, row.title, row.file_path)
            if month_key and media_key:
                bucket["_unique_titles_monthly"].add((month_key, media_key))

            if row.media_type == MediaType.MOVIE:
                bucket["movie_sessions"] += 1
                bucket["movie_watch_ms"] += watch_ms
                if month_key and media_key:
                    bucket["_unique_movies_monthly"].add((month_key, media_key))
            elif row.media_type == MediaType.EPISODE:
                bucket["episode_sessions"] += 1
                bucket["episode_watch_ms"] += watch_ms
                series_key = self._series_key(row.series_title, row.title_clean, row.title, row.file_path)
                if month_key and series_key:
                    bucket["_unique_series_monthly"].add((month_key, series_key))

            if row.updated_at and (bucket["last_seen_at"] is None or row.updated_at > bucket["last_seen_at"]):
                bucket["last_seen_at"] = row.updated_at

            local_hour = self._local_hour(row.started_at)
            if local_hour is not None:
                hour_counts[local_hour] += 1

        items = []
        for stats in per_user.values():
            items.append(
                {
                    "user_name": stats["user_name"],
                    "total_sessions": stats["total_sessions"],
                    "movie_sessions": stats["movie_sessions"],
                    "episode_sessions": stats["episode_sessions"],
                    "total_watch_hours": round(stats["total_watch_ms"] / 3_600_000, 2),
                    "movie_watch_hours": round(stats["movie_watch_ms"] / 3_600_000, 2),
                    "episode_watch_hours": round(stats["episode_watch_ms"] / 3_600_000, 2),
                    "unique_titles_monthly": len(stats["_unique_titles_monthly"]),
                    "unique_movies_monthly": len(stats["_unique_movies_monthly"]),
                    "unique_series_monthly": len(stats["_unique_series_monthly"]),
                    "last_seen_at": stats["last_seen_at"],
                }
            )

        items.sort(key=lambda item: (item["total_sessions"], item["total_watch_hours"]), reverse=True)

        leaders = {
            "most_sessions_user": self._leader(items, "total_sessions"),
            "most_watch_hours_user": self._leader(items, "total_watch_hours"),
            "most_movies_user": self._leader(items, "unique_movies_monthly"),
            "most_series_user": self._leader(items, "unique_series_monthly"),
        }

        peak_hours = [
            {
                "hour": hour,
                "sessions": count,
            }
            for hour, count in enumerate(hour_counts)
        ]

        return {
            "items": items[:limit],
            "leaders": leaders,
            "peak_hours": peak_hours,
            "timezone": str(self.timezone),
            "play_count_rule": "history_counts_every_session;unique_play_counts_once_per_user_title_per_month",
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

    def _load_timezone(self) -> ZoneInfo:
        row = self.db.scalar(select(AppSettingModel).where(AppSettingModel.key == "timezone"))
        value = (row.value.strip() if row and row.value else "UTC")
        try:
            return ZoneInfo(value)
        except Exception:
            return ZoneInfo("UTC")

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
    def _resolve_watch_ms(duration_ms: int | None, started_at: datetime | None, ended_at: datetime | None) -> int:
        if isinstance(duration_ms, int) and duration_ms > 0:
            return duration_ms
        if started_at and ended_at and ended_at > started_at:
            return int((ended_at - started_at).total_seconds() * 1000)
        return 0

    @staticmethod
    def _media_key(title_clean: str | None, title: str | None, file_path: str | None) -> str:
        source = title_clean or title or file_path or "unknown"
        return str(source).strip().lower()

    @staticmethod
    def _series_key(series_title: str | None, title_clean: str | None, title: str | None, file_path: str | None) -> str:
        source = series_title or title_clean or title or file_path or "unknown"
        return str(source).strip().lower()

    def _month_key(self, started_at: datetime | None) -> str | None:
        if started_at is None:
            return None
        return started_at.astimezone(self.timezone).strftime("%Y-%m")

    def _local_hour(self, started_at: datetime | None) -> int | None:
        if started_at is None:
            return None
        return started_at.astimezone(self.timezone).hour

    @staticmethod
    def _leader(items: list[dict], metric: str) -> dict:
        if not items:
            return {"user_name": "n/a", "value": 0}
        winner = max(items, key=lambda item: item.get(metric, 0))
        return {
            "user_name": winner.get("user_name", "n/a"),
            "value": winner.get(metric, 0),
        }

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
