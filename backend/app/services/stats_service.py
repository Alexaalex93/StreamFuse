from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from zoneinfo import ZoneInfo

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.persistence.models.app_setting import AppSettingModel
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.services.unraid_metrics_service import UnraidMetricsService
from app.services.user_alias_service import UserAliasService


@dataclass(slots=True)
class StatsFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    user_name: str | None = None


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

        aggregate_rows = self.db.execute(
            select(
                UnifiedStreamSessionModel.started_at,
                UnifiedStreamSessionModel.bandwidth_bps,
            ).where(*self._where(filters))
        ).all()

        sessions_by_day: dict[str, int] = {}
        sessions_by_week: dict[str, int] = {}
        sessions_by_month: dict[str, int] = {}
        sessions_by_year: dict[str, int] = {}

        bandwidth_day_acc: dict[str, list[float]] = {}
        bandwidth_week_acc: dict[str, list[float]] = {}
        bandwidth_month_acc: dict[str, list[float]] = {}
        bandwidth_year_acc: dict[str, list[float]] = {}

        for row in aggregate_rows:
            local_dt = self._to_local_datetime(row.started_at)
            if local_dt is None:
                continue

            day_key = local_dt.strftime("%Y-%m-%d")
            week_key = self._week_key(local_dt)
            month_key = local_dt.strftime("%Y-%m")
            year_key = local_dt.strftime("%Y")

            sessions_by_day[day_key] = sessions_by_day.get(day_key, 0) + 1
            sessions_by_week[week_key] = sessions_by_week.get(week_key, 0) + 1
            sessions_by_month[month_key] = sessions_by_month.get(month_key, 0) + 1
            sessions_by_year[year_key] = sessions_by_year.get(year_key, 0) + 1

            if row.bandwidth_bps is not None:
                value = float(row.bandwidth_bps)
                bandwidth_day_acc.setdefault(day_key, []).append(value)
                bandwidth_week_acc.setdefault(week_key, []).append(value)
                bandwidth_month_acc.setdefault(month_key, []).append(value)
                bandwidth_year_acc.setdefault(year_key, []).append(value)

        per_day = [{"day": key, "sessions": sessions_by_day[key]} for key in sorted(sessions_by_day.keys())]
        per_week = [{"day": key, "sessions": sessions_by_week[key]} for key in sorted(sessions_by_week.keys())]
        per_month = [{"day": key, "sessions": sessions_by_month[key]} for key in sorted(sessions_by_month.keys())]
        per_year = [{"day": key, "sessions": sessions_by_year[key]} for key in sorted(sessions_by_year.keys())]

        bandwidth_day = self._avg_points(bandwidth_day_acc)
        bandwidth_week = self._avg_points(bandwidth_week_acc)
        bandwidth_month = self._avg_points(bandwidth_month_acc)
        bandwidth_year = self._avg_points(bandwidth_year_acc)

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
                UnifiedStreamSessionModel.source,
                UnifiedStreamSessionModel.status,
                UnifiedStreamSessionModel.raw_payload,
                UnifiedStreamSessionModel.file_path,
                UnifiedStreamSessionModel.started_at,
                UnifiedStreamSessionModel.ended_at,
                UnifiedStreamSessionModel.updated_at,
                UnifiedStreamSessionModel.bandwidth_bps,
                UnifiedStreamSessionModel.progress_percent,
                UnifiedStreamSessionModel.duration_ms,
            ).where(*self._where(filters))
        ).all()
        total_shared_bytes = 0
        shared_by_day: dict[str, int] = {}
        shared_by_week: dict[str, int] = {}
        shared_by_month: dict[str, int] = {}
        shared_by_year: dict[str, int] = {}
        shared_by_hour: dict[int, int] = {hour: 0 for hour in range(24)}

        for row in shared_rows:
            shared_bytes = self._extract_shared_bytes(row)
            if shared_bytes <= 0:
                continue

            total_shared_bytes += shared_bytes

            local_dt = self._to_local_datetime(row.started_at)
            if local_dt is None:
                continue

            day_key = local_dt.strftime("%Y-%m-%d")
            week_key = self._week_key(local_dt)
            month_key = local_dt.strftime("%Y-%m")
            year_key = local_dt.strftime("%Y")

            shared_by_day[day_key] = shared_by_day.get(day_key, 0) + shared_bytes
            shared_by_week[week_key] = shared_by_week.get(week_key, 0) + shared_bytes
            shared_by_month[month_key] = shared_by_month.get(month_key, 0) + shared_bytes
            shared_by_year[year_key] = shared_by_year.get(year_key, 0) + shared_bytes
            shared_by_hour[local_dt.hour] = shared_by_hour.get(local_dt.hour, 0) + shared_bytes

        unraid_metrics = UnraidMetricsService(self.db, self._settings()).get_metrics()
        if unraid_metrics.enabled and unraid_metrics.source_available:
            use_unraid_totals = self._setting_bool("use_unraid_totals", default=False)
            if use_unraid_totals and unraid_metrics.total_shared_bytes is not None:
                total_shared_bytes = int(unraid_metrics.total_shared_bytes)

        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekday_counts = [0] * 7
        hour_counts = [0] * 24
        platform_counts: dict[str, int] = {}
        media_type_counts = {"movie": 0, "series": 0, "other": 0}

        distribution_rows = self.db.execute(
            select(
                UnifiedStreamSessionModel.started_at,
                UnifiedStreamSessionModel.client_name,
                UnifiedStreamSessionModel.player_name,
                UnifiedStreamSessionModel.media_type,
            ).where(*self._where(filters))
        ).all()

        for row in distribution_rows:
            local_dt = self._to_local_datetime(row.started_at)
            if local_dt:
                weekday_counts[local_dt.weekday()] += 1
                hour_counts[local_dt.hour] += 1

            platform = self._platform_name(row.client_name, row.player_name)
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

            media_key = self._media_type_bucket(row.media_type)
            media_type_counts[media_key] = media_type_counts.get(media_key, 0) + 1

        play_count_by_platform = [
            {"label": key, "sessions": value}
            for key, value in sorted(platform_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ]

        return {
            "total_sessions": int(totals.total_sessions or 0),
            "active_sessions": int(totals.active_sessions or 0),
            "ended_sessions": int(totals.ended_sessions or 0),
            "stale_sessions": int(totals.stale_sessions or 0),
            "total_shared_bytes": int(total_shared_bytes),
            "total_shared_human": _format_bytes(total_shared_bytes),
            "sessions_by_day": [{"day": row["day"], "sessions": int(row["sessions"])} for row in per_day],
            "sessions_by_week": [{"day": row["day"], "sessions": int(row["sessions"])} for row in per_week],
            "sessions_by_month": [{"day": row["day"], "sessions": int(row["sessions"])} for row in per_month],
            "sessions_by_year": [{"day": row["day"], "sessions": int(row["sessions"])} for row in per_year],
            "bandwidth_by_day": [
                {"day": row["day"], "avg_bandwidth_bps": float(row["avg_bandwidth_bps"])}
                for row in bandwidth_day
            ],
            "bandwidth_by_week": [
                {"day": row["day"], "avg_bandwidth_bps": float(row["avg_bandwidth_bps"])}
                for row in bandwidth_week
            ],
            "bandwidth_by_month": [
                {"day": row["day"], "avg_bandwidth_bps": float(row["avg_bandwidth_bps"])}
                for row in bandwidth_month
            ],
            "bandwidth_by_year": [
                {"day": row["day"], "avg_bandwidth_bps": float(row["avg_bandwidth_bps"])}
                for row in bandwidth_year
            ],
            "source_distribution": [
                {"source": row.source.value if row.source else "unknown", "sessions": int(row.sessions or 0)}
                for row in source_distribution
            ],
            "active_by_source": [
                {"source": row.source.value if row.source else "unknown", "sessions": int(row.sessions or 0)}
                for row in active_by_source
            ],
            "play_count_by_weekday": [
                {"label": weekday_names[index], "sessions": int(count)}
                for index, count in enumerate(weekday_counts)
            ],
            "play_count_by_hour": [
                {"hour": hour, "sessions": int(count)}
                for hour, count in enumerate(hour_counts)
            ],
            "play_count_by_platform": play_count_by_platform,
            "play_count_by_media_type": [
                {"label": "movie", "sessions": int(media_type_counts.get("movie", 0))},
                {"label": "series", "sessions": int(media_type_counts.get("series", 0))},
                {"label": "other", "sessions": int(media_type_counts.get("other", 0))},
            ],
            "shared_by_day": [
                {"day": key, "shared_bytes": int(shared_by_day[key])}
                for key in sorted(shared_by_day.keys())
            ],
            "shared_by_week": [
                {"day": key, "shared_bytes": int(shared_by_week[key])}
                for key in sorted(shared_by_week.keys())
            ],
            "shared_by_month": [
                {"day": key, "shared_bytes": int(shared_by_month[key])}
                for key in sorted(shared_by_month.keys())
            ],
            "shared_by_year": [
                {"day": key, "shared_bytes": int(shared_by_year[key])}
                for key in sorted(shared_by_year.keys())
            ],
            "shared_by_hour": [
                {"hour": hour, "shared_bytes": int(shared_by_hour.get(hour, 0))}
                for hour in range(24)
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
            UnifiedStreamSessionModel.season_number,
            UnifiedStreamSessionModel.episode_number,
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
            media_key = self._media_key(
                row.media_type,
                row.title_clean,
                row.title,
                row.file_path,
                row.season_number,
                row.episode_number,
            )
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
                series_key = self._series_key(
                    row.series_title,
                    row.title_clean,
                    row.title,
                    row.file_path,
                )
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
        stmt = select(
            UnifiedStreamSessionModel.id,
            UnifiedStreamSessionModel.media_type,
            UnifiedStreamSessionModel.title,
            UnifiedStreamSessionModel.title_clean,
            UnifiedStreamSessionModel.series_title,
            UnifiedStreamSessionModel.file_path,
            UnifiedStreamSessionModel.user_name,
            UnifiedStreamSessionModel.bandwidth_bps,
            UnifiedStreamSessionModel.season_number,
            UnifiedStreamSessionModel.episode_number,
        ).where(*self._where(filters), UnifiedStreamSessionModel.media_type == media_type)

        rows = self.db.execute(stmt).all()

        grouped: dict[str, dict] = {}
        for row in rows:
            if by_series:
                key = self._series_key(row.series_title, row.title_clean, row.title, row.file_path)
                display = self._series_display_title(row.series_title, row.title_clean, row.title, row.file_path)
            else:
                key = self._media_key(
                    row.media_type,
                    row.title_clean,
                    row.title,
                    row.file_path,
                    row.season_number,
                    row.episode_number,
                )
                display = self._media_display_title(row.title, row.title_clean, row.file_path)

            bucket = grouped.setdefault(
                key,
                {
                    "title": display,
                    "media_type": row.media_type.value if row.media_type else "unknown",
                    "sessions": 0,
                    "users": set(),
                    "bandwidth_values": [],
                    "sample_session_id": row.id,
                },
            )

            bucket["sessions"] += 1
            if row.user_name:
                bucket["users"].add(str(row.user_name).strip().lower())
            if row.bandwidth_bps is not None:
                bucket["bandwidth_values"].append(float(row.bandwidth_bps))
            if not bucket["title"] and display:
                bucket["title"] = display

        items = []
        for data in grouped.values():
            values = data["bandwidth_values"]
            avg_bandwidth = (sum(values) / len(values)) if values else None
            items.append(
                {
                    "title": data["title"] or "unknown",
                    "media_type": data["media_type"],
                    "sessions": int(data["sessions"]),
                    "unique_users": int(len(data["users"])),
                    "avg_bandwidth_bps": avg_bandwidth,
                    "sample_session_id": data["sample_session_id"],
                }
            )

        items.sort(key=lambda item: (item["unique_users"], item["sessions"]), reverse=True)
        return items[:limit]

    def _load_timezone(self) -> ZoneInfo:
        row = self.db.scalar(select(AppSettingModel).where(AppSettingModel.key == "timezone"))
        value = (row.value.strip() if row and row.value else "UTC")
        try:
            return ZoneInfo(value)
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def _extract_shared_bytes(row: object) -> int:
        source = getattr(row, "source", None)
        status = getattr(row, "status", None)
        raw_payload = getattr(row, "raw_payload", None)
        file_path = getattr(row, "file_path", None)
        started_at = getattr(row, "started_at", None)
        ended_at = getattr(row, "ended_at", None)
        updated_at = getattr(row, "updated_at", None)
        bandwidth_bps = getattr(row, "bandwidth_bps", None)
        progress_percent = getattr(row, "progress_percent", None)
        duration_ms = getattr(row, "duration_ms", None)

        if not isinstance(raw_payload, dict):
            raw_payload = {}

        def _clamp_ratio(value: float | None) -> float | None:
            if value is None:
                return None
            return max(0.0, min(1.0, value))

        def _numeric(value: object) -> int | None:
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
            return None

        bytes_sent = _numeric(raw_payload.get("bytes_sent"))
        if bytes_sent:
            return bytes_sent

        connection = raw_payload.get("connection")
        if isinstance(connection, dict):
            conn_sent = _numeric(connection.get("bytes_sent"))
            if conn_sent:
                return conn_sent

            transfer = raw_payload.get("transfer")
            if isinstance(transfer, dict):
                transfer_size = _numeric(transfer.get("size"))
                if transfer_size:
                    return transfer_size

            transfers = connection.get("active_transfers")
            if isinstance(transfers, list):
                sizes = []
                for item in transfers:
                    if not isinstance(item, dict):
                        continue
                    # SFTPGo API v2 uses type=1 for downloads (integer);
                    # older/other adapters may use operation_type="download" (string)
                    is_download = (
                        item.get("type") == 1
                        or str(item.get("operation_type") or "").lower() == "download"
                    )
                    if not is_download:
                        continue
                    size = _numeric(item.get("size"))
                    if size:
                        sizes.append(size)
                if sizes:
                    return max(sizes)

        file_size = _numeric(raw_payload.get("file_size"))

        ratio: float | None = None
        view_offset = raw_payload.get("view_offset")
        if isinstance(view_offset, (int, float)) and isinstance(duration_ms, (int, float)) and duration_ms and duration_ms > 0:
            ratio = _clamp_ratio(float(view_offset) / float(duration_ms))

        if ratio is None and isinstance(progress_percent, (int, float)):
            ratio = _clamp_ratio(float(progress_percent) / 100.0)

        if ratio is None and started_at and duration_ms and isinstance(duration_ms, (int, float)) and duration_ms > 0:
            end_ref = ended_at or updated_at or datetime.now(tz=started_at.tzinfo)
            if end_ref and end_ref > started_at:
                elapsed_ms = (end_ref - started_at).total_seconds() * 1000.0
                ratio = _clamp_ratio(elapsed_ms / float(duration_ms))

        if file_size:
            if ratio is not None and ratio > 0:
                estimate = int(file_size * ratio)
                if estimate > 0:
                    return estimate
            if source == StreamSource.TAUTULLI and status == SessionStatus.ENDED:
                return file_size

        if bandwidth_bps and started_at:
            end_ref = ended_at or updated_at or datetime.now(tz=started_at.tzinfo)
            if end_ref and end_ref > started_at:
                elapsed_sec = (end_ref - started_at).total_seconds()
                estimate = int((float(bandwidth_bps) / 8.0) * elapsed_sec)
                if file_size:
                    return max(0, min(file_size, estimate))
                if estimate > 0:
                    return estimate

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
    def _extract_tmdb_id(file_path: str | None) -> str | None:
        if not file_path:
            return None
        match = re.search(r"\{tmdb-(\d+)\}", str(file_path), flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _extract_episode_code(
        season_number: int | None,
        episode_number: int | None,
        title: str | None,
        file_path: str | None,
    ) -> str | None:
        if season_number is not None and episode_number is not None:
            return f"S{season_number:02d}E{episode_number:02d}"

        for source in (title, file_path):
            if not source:
                continue
            match = re.search(r"S(\d{1,2})E(\d{1,2})", str(source), flags=re.IGNORECASE)
            if match:
                return f"S{int(match.group(1)):02d}E{int(match.group(2)):02d}"

        return None

    @staticmethod
    def _base_series_name(series_title: str | None, file_path: str | None, fallback: str | None) -> str:
        if series_title:
            return str(series_title).strip().lower()

        if file_path:
            normalized = str(file_path).replace("\\", "/")
            match = re.search(r"/(series|tvshows?)/([^/]+)", normalized, flags=re.IGNORECASE)
            if match:
                folder = match.group(2)
                folder = re.sub(r"\s*\{tmdb-\d+\}\s*", "", folder, flags=re.IGNORECASE)
                return folder.strip().lower()

        return str(fallback or "unknown").strip().lower()

    def _media_key(
        self,
        media_type: MediaType | None,
        title_clean: str | None,
        title: str | None,
        file_path: str | None,
        season_number: int | None,
        episode_number: int | None,
    ) -> str:
        tmdb_id = self._extract_tmdb_id(file_path)

        if media_type == MediaType.EPISODE:
            episode_code = self._extract_episode_code(season_number, episode_number, title, file_path)
            series_base = self._base_series_name(None, file_path, title_clean or title)
            if tmdb_id and episode_code:
                return f"episode:tmdb:{tmdb_id}:{episode_code}"
            if episode_code:
                return f"episode:{series_base}:{episode_code}"
            if tmdb_id:
                return f"episode:tmdb:{tmdb_id}"

        if tmdb_id:
            return f"movie:tmdb:{tmdb_id}"

        source = title_clean or title or file_path or "unknown"
        return str(source).strip().lower()

    @staticmethod
    def _series_key(series_title: str | None, title_clean: str | None, title: str | None, file_path: str | None) -> str:
        tmdb_id = StatsService._extract_tmdb_id(file_path)
        if tmdb_id:
            return f"series:tmdb:{tmdb_id}"

        source = StatsService._base_series_name(series_title, file_path, title_clean or title)
        return f"series:{source}"

    @staticmethod
    def _media_display_title(title: str | None, title_clean: str | None, file_path: str | None) -> str:
        for value in (title, title_clean):
            if value and str(value).strip():
                return str(value).strip()
        if file_path:
            return str(file_path).replace("\\", "/").rsplit("/", 1)[-1]
        return "unknown"

    @staticmethod
    def _series_display_title(series_title: str | None, title_clean: str | None, title: str | None, file_path: str | None) -> str:
        if series_title and str(series_title).strip():
            return str(series_title).strip()

        if file_path:
            normalized = str(file_path).replace("\\", "/")
            match = re.search(r"/(series|tvshows?)/([^/]+)", normalized, flags=re.IGNORECASE)
            if match:
                folder = re.sub(r"\s*\{tmdb-\d+\}\s*", "", match.group(2), flags=re.IGNORECASE).strip()
                if folder:
                    return folder

        return StatsService._media_display_title(title, title_clean, file_path)

    @staticmethod
    def _week_key(local_dt: datetime) -> str:
        iso_year, iso_week, _ = local_dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @staticmethod
    def _avg_points(values_by_key: dict[str, list[float]]) -> list[dict[str, float | str]]:
        points: list[dict[str, float | str]] = []
        for key in sorted(values_by_key.keys()):
            values = values_by_key[key]
            avg = (sum(values) / len(values)) if values else 0.0
            points.append({"day": key, "avg_bandwidth_bps": float(avg)})
        return points
    def _month_key(self, started_at: datetime | None) -> str | None:
        local_dt = self._to_local_datetime(started_at)
        if local_dt is None:
            return None
        return local_dt.strftime("%Y-%m")

    def _local_hour(self, started_at: datetime | None) -> int | None:
        local_dt = self._to_local_datetime(started_at)
        if local_dt is None:
            return None
        return local_dt.hour

    def _to_local_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(self.timezone)
    @staticmethod
    def _platform_name(client_name: str | None, player_name: str | None) -> str:
        for value in (client_name, player_name):
            if value and str(value).strip():
                return str(value).strip()
        return "Unknown"

    @staticmethod
    def _media_type_bucket(media_type: MediaType | None) -> str:
        if media_type == MediaType.MOVIE:
            return "movie"
        if media_type == MediaType.EPISODE:
            return "series"
        return "other"

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
    def _settings() -> Settings:
        return get_settings()

    def _setting_bool(self, key: str, default: bool = False) -> bool:
        row = self.db.scalar(select(AppSettingModel).where(AppSettingModel.key == key))
        if row is None:
            return default
        return str(row.value).strip().lower() in {"1", "true", "yes", "on"}

    def _where(self, filters: StatsFilters) -> list:
        clauses = []
        if filters.date_from:
            clauses.append(UnifiedStreamSessionModel.started_at >= filters.date_from)
        if filters.date_to:
            clauses.append(UnifiedStreamSessionModel.started_at <= filters.date_to)
        if filters.user_name:
            candidates = self.alias_service.candidate_raw_usernames(filters.user_name)
            if candidates:
                clauses.append(UnifiedStreamSessionModel.user_name.in_(list(candidates)))
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






























































