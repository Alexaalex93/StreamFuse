from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import MediaType, SessionStatus, StreamSource
from app.parsers.media_parser import clean_movie_title, parse_series_context


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


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _guess_media_type(raw_type: str | None) -> MediaType:
    if not raw_type:
        return MediaType.OTHER

    value = raw_type.lower()
    if value in {"movie", "clip"}:
        return MediaType.MOVIE
    if value in {"episode", "show", "season"}:
        return MediaType.EPISODE
    if value in {"live", "livetv"}:
        return MediaType.LIVE
    return MediaType.OTHER


def _format_bandwidth_human(kbps: int | None) -> str | None:
    if kbps is None:
        return None

    mbps = kbps / 1000
    if mbps >= 1:
        return f"{mbps:.1f} Mbps"
    return f"{kbps} Kbps"


def _source_session_id(payload: dict[str, Any]) -> str:
    for key in ("session_id", "id", "reference_id", "rating_key"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    stamp = payload.get("started") or payload.get("date") or "unknown"
    user = payload.get("user") or "user"
    return f"tautulli-{user}-{stamp}"


def map_tautulli_payload(payload: dict[str, Any], *, historical: bool = False) -> UnifiedStreamSessionCreate:
    file_path = payload.get("file")
    file_name = PurePath(str(file_path)).name if file_path else None

    media_type = _guess_media_type(payload.get("media_type"))
    parsed_series = parse_series_context(str(file_path)) if file_path else {
        "series_title": None,
        "season_number": None,
        "episode_number": None,
    }

    title = payload.get("full_title") or payload.get("title") or file_name
    title_clean = clean_movie_title(str(title or ""))

    duration_ms = _to_int(payload.get("duration"))
    if duration_ms is not None and duration_ms < 10000:
        duration_ms *= 1000

    bitrate_kbps = _to_int(payload.get("stream_bitrate") or payload.get("bandwidth"))
    bandwidth_bps = bitrate_kbps * 1000 if bitrate_kbps is not None else None

    started_at = _to_datetime(payload.get("started") or payload.get("date"))
    ended_at = _to_datetime(payload.get("stopped"))

    status = SessionStatus.ENDED if historical or ended_at else SessionStatus.ACTIVE

    transcode_decision = payload.get("transcode_decision")
    if not transcode_decision:
        transcode_decision = "direct play" if payload.get("stream_bitrate") else "unknown"

    return UnifiedStreamSessionCreate(
        source=StreamSource.TAUTULLI,
        source_session_id=_source_session_id(payload),
        status=status,
        user_name=str(payload.get("user") or "unknown"),
        ip_address=payload.get("ip_address"),
        title=title,
        title_clean=title_clean,
        media_type=media_type,
        series_title=(payload.get("grandparent_title") or parsed_series.get("series_title")),
        season_number=_to_int(payload.get("parent_media_index")) or parsed_series.get("season_number"),
        episode_number=_to_int(payload.get("media_index")) or parsed_series.get("episode_number"),
        file_path=file_path,
        file_name=file_name,
        poster_path=payload.get("thumb") or payload.get("parent_thumb") or payload.get("grandparent_thumb"),
        bandwidth_bps=bandwidth_bps,
        bandwidth_human=_format_bandwidth_human(bitrate_kbps),
        started_at=started_at,
        ended_at=ended_at,
        progress_percent=_to_float(payload.get("progress_percent")),
        duration_ms=duration_ms,
        client_name=payload.get("platform") or payload.get("product"),
        player_name=payload.get("player") or payload.get("product"),
        transcode_decision=transcode_decision,
        resolution=payload.get("stream_video_full_resolution") or payload.get("video_resolution"),
        video_codec=payload.get("stream_video_codec") or payload.get("video_codec"),
        audio_codec=payload.get("stream_audio_codec") or payload.get("audio_codec"),
        raw_payload=payload,
    )
