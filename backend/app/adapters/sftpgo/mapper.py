from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.parsers.media_parser import clean_movie_title, detect_media_type, parse_series_context
from app.parsers.mediainfo_parser import MediaInfoSummary


def _to_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, str) and value.isdigit():
        value = int(value)

    if isinstance(value, (int, float)):
        if value > 1_000_000_000_000:
            return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(value, tz=timezone.utc)

    return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _format_bps(bps: int | None) -> str | None:
    if bps is None:
        return None
    mbps = bps / 1_000_000
    if mbps >= 1:
        return f"{mbps:.1f} Mbps"
    kbps = bps / 1_000
    return f"{kbps:.1f} Kbps"


def _earliest_log_datetime(logs: list[dict[str, Any]]) -> datetime | None:
    earliest: datetime | None = None
    for item in logs:
        candidate = _to_datetime(item.get("ts")) or _to_datetime(item.get("timestamp"))
        if candidate is None:
            continue
        if earliest is None or candidate < earliest:
            earliest = candidate
    return earliest


def build_sftpgo_session_payload(
    *,
    source_session_id: str,
    connection: dict[str, Any],
    related_logs: list[dict[str, Any]],
    status: SessionStatus,
    bandwidth_bps: int | None,
    poster_path: str | None,
    media_info: MediaInfoSummary | None = None,
    ended_at: datetime | None = None,
) -> UnifiedStreamSessionCreate:
    file_path = (
        connection.get("file_path")
        or connection.get("path")
        or connection.get("current_path")
        or _best_log_field(related_logs, "file_path")
        or _best_log_field(related_logs, "path")
    )

    file_name = PurePath(str(file_path)).name if file_path else None
    media_type = detect_media_type(str(file_path)) if file_path else MediaType.OTHER
    series_ctx = parse_series_context(str(file_path)) if file_path else {
        "series_title": None,
        "season_number": None,
        "episode_number": None,
    }

    raw_title = media_info.title if media_info and media_info.title else (file_name or source_session_id)
    title = clean_movie_title(raw_title)

    started_at = (
        _to_datetime(connection.get("start_time"))
        or _to_datetime(connection.get("connected_at"))
        or _to_datetime(connection.get("connection_time"))
        or _earliest_log_datetime(related_logs)
    )

    bytes_sent = _to_int(connection.get("bytes_sent"))
    bytes_received = _to_int(connection.get("bytes_received"))
    media_info_dict = media_info.to_dict() if media_info else None

    return UnifiedStreamSessionCreate(
        source=StreamSource.SFTPGO,
        source_session_id=source_session_id,
        status=status,
        user_name=str(connection.get("username") or _best_log_field(related_logs, "username") or "unknown"),
        ip_address=str(
            connection.get("ip_address")
            or connection.get("remote_address")
            or _best_log_field(related_logs, "ip_address")
            or ""
        )
        or None,
        title=title,
        title_clean=title,
        media_type=media_type,
        series_title=series_ctx.get("series_title"),
        season_number=series_ctx.get("season_number"),
        episode_number=series_ctx.get("episode_number"),
        file_path=file_path,
        file_name=file_name,
        poster_path=poster_path,
        bandwidth_bps=bandwidth_bps,
        bandwidth_human=_format_bps(bandwidth_bps),
        started_at=started_at,
        ended_at=ended_at,
        progress_percent=None,
        duration_ms=media_info.duration_ms if media_info else None,
        client_name=connection.get("protocol") or _best_log_field(related_logs, "protocol"),
        player_name=connection.get("protocol") or "SFTP Client",
        transcode_decision="direct play",
        resolution=media_info.resolution if media_info else None,
        video_codec=media_info.video_codec if media_info else None,
        audio_codec=media_info.audio_codec if media_info else None,
        raw_payload={
            "connection": connection,
            "logs": related_logs,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "media_info": media_info_dict,
        },
    )


def _best_log_field(logs: list[dict[str, Any]], field: str) -> Any:
    for item in reversed(logs):
        value = item.get(field)
        if value not in (None, ""):
            return value
    return None
