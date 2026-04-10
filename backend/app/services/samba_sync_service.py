from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.adapters.samba.client import SambaClient
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.media_parser import clean_movie_title, detect_media_type, parse_series_context
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService

_MEDIA_FILE_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".m4v",
    ".ts",
    ".m2ts",
    ".mts",
    ".wmv",
    ".flv",
    ".webm",
    ".mpg",
    ".mpeg",
    ".vob",
    ".iso",
    ".3gp",
    ".3g2",
    ".ogv",
    ".rmvb",
    ".divx",
    ".xvid",
}


class SambaSyncService:
    def __init__(
        self,
        client: SambaClient,
        session_service: SessionService,
        poster_resolver: PosterResolver,
        stale_seconds: int = 180,
        path_mappings: list[str] | None = None,
    ) -> None:
        self.client = client
        self.session_service = session_service
        self.poster_resolver = poster_resolver
        self.stale_seconds = stale_seconds
        self.path_mappings = self._parse_path_mappings(path_mappings or [])
        self._active_session_ids_by_key: dict[str, str] = {}
        self._key_by_session_id: dict[str, str] = {}

    async def poll_once(self) -> dict[str, int]:
        self._rebuild_active_session_cache()

        connections = await self.client.fetch_active_connections()
        grouped = self._group_download_connections(connections)

        seen_ids: set[str] = set()
        imported = 0
        errors = 0

        for item in grouped:
            try:
                logical_key = item["logical_key"]
                source_session_id = self._resolve_session_id_for_key(logical_key)
                seen_ids.add(source_session_id)

                media_path = self._normalize_media_path_for_local_fs(item["file_path"])
                if not media_path or not self._looks_like_media_file(media_path):
                    continue

                media_info = parse_mediainfo_for_media(media_path)
                poster = self.poster_resolver.resolve(media_path, None)
                series_ctx = parse_series_context(media_path)
                media_type = detect_media_type(media_path)
                file_name = Path(media_path).name

                series_title = _clean_display_text(str(series_ctx.get("series_title") or "")) or None
                season_number = series_ctx.get("season_number")
                episode_number = series_ctx.get("episode_number")

                media_title = _clean_display_text(media_info.title) if media_info and media_info.title else ""
                fallback_title = clean_movie_title(file_name)
                base_title = media_title or _clean_display_text(fallback_title)

                if media_type.value == "episode":
                    title = _format_episode_title(series_title, base_title, season_number, episode_number)
                    title_clean = _clean_display_text(title)
                else:
                    title = _clean_display_text(base_title)
                    title_clean = _clean_display_text(clean_movie_title(title or fallback_title))

                transfer = item.get("transfer") if isinstance(item.get("transfer"), dict) else {}
                size = _to_int(transfer.get("size"))
                start_time = _to_datetime(transfer.get("start_time"))
                connection_time = _to_datetime(item["connection"].get("connection_time"))
                started_at = start_time or connection_time or datetime.now(UTC)

                bandwidth_bps = None
                if size and start_time:
                    elapsed = max((datetime.now(UTC) - start_time).total_seconds(), 1)
                    bandwidth_bps = int(size / elapsed)

                payload = UnifiedStreamSessionCreate(
                    source=StreamSource.SAMBA,
                    source_session_id=source_session_id,
                    status=SessionStatus.ACTIVE,
                    user_name=str(item["connection"].get("username") or "unknown"),
                    ip_address=_normalize_ip(str(item["connection"].get("remote_address") or "")) or None,
                    title=title,
                    title_clean=title_clean,
                    media_type=media_type,
                    series_title=series_title,
                    season_number=season_number,
                    episode_number=episode_number,
                    file_path=media_path,
                    file_name=file_name,
                    poster_path=str(poster),
                    bandwidth_bps=bandwidth_bps,
                    bandwidth_human=_format_bps(bandwidth_bps),
                    started_at=started_at,
                    ended_at=None,
                    duration_ms=media_info.duration_ms if media_info else None,
                    client_name=str(item["connection"].get("protocol") or "SMB"),
                    player_name="SMB",
                    transcode_decision="direct play",
                    resolution=media_info.resolution if media_info else None,
                    video_codec=media_info.video_codec if media_info else None,
                    audio_codec=media_info.audio_codec if media_info else None,
                    raw_payload={
                        "connection": item["connection"],
                        "transfer": transfer,
                        "media_info": media_info.to_dict() if media_info else None,
                    },
                )
                self.session_service.create_session(payload)
                imported += 1
            except Exception:
                errors += 1

        stale_marked = self._mark_stale_sessions(seen_ids)
        self._rebuild_active_session_cache()

        return {
            "active_imported": imported,
            "stale_marked": stale_marked,
            "errors": errors,
            "total_processed": imported + stale_marked,
        }

    def _group_download_connections(self, connections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for conn in connections:
            username = str(conn.get("username") or "").strip()
            if not username:
                continue
            ip_value = _normalize_ip(str(conn.get("remote_address") or ""))
            transfers = conn.get("active_transfers")
            if not isinstance(transfers, list):
                continue

            for transfer in transfers:
                if not isinstance(transfer, dict):
                    continue
                op = str(transfer.get("operation_type") or "").lower()
                if op != "download":
                    continue
                file_path = str(transfer.get("path") or "").strip()
                if not file_path or not self._looks_like_media_file(file_path):
                    continue

                key = f"{username.lower()}|{ip_value}|{file_path.lower()}"
                existing = grouped.get(key)
                if existing is None:
                    grouped[key] = {
                        "logical_key": key,
                        "connection": conn,
                        "transfer": transfer,
                        "file_path": file_path,
                    }
                    continue

                existing_size = _to_int(existing.get("transfer", {}).get("size") if isinstance(existing.get("transfer"), dict) else None) or 0
                current_size = _to_int(transfer.get("size")) or 0
                if current_size >= existing_size:
                    grouped[key] = {
                        "logical_key": key,
                        "connection": conn,
                        "transfer": transfer,
                        "file_path": file_path,
                    }

        return list(grouped.values())

    def _rebuild_active_session_cache(self) -> None:
        self._active_session_ids_by_key = {}
        self._key_by_session_id = {}

        rows = self.session_service.repository.list_active_by_source(StreamSource.SAMBA)
        for row in rows:
            file_path = (row.file_path or "").strip()
            user_name = (row.user_name or "").strip()
            ip_value = _normalize_ip(row.ip_address or "")
            if not file_path or not user_name:
                continue
            key = f"{user_name.lower()}|{ip_value}|{file_path.lower()}"
            self._active_session_ids_by_key[key] = row.source_session_id
            self._key_by_session_id[row.source_session_id] = key

    def _resolve_session_id_for_key(self, logical_key: str) -> str:
        existing = self._active_session_ids_by_key.get(logical_key)
        if existing:
            return existing

        stamp = int(datetime.now(UTC).timestamp() * 1000)
        slug = abs(hash(logical_key))
        source_session_id = f"samba-{slug}-{stamp}"
        self._active_session_ids_by_key[logical_key] = source_session_id
        self._key_by_session_id[source_session_id] = logical_key
        return source_session_id

    def _mark_stale_sessions(self, active_ids: set[str]) -> int:
        now = datetime.now(UTC)
        stale_threshold = now - timedelta(seconds=self.stale_seconds)
        rows = self.session_service.repository.list_active_by_source(StreamSource.SAMBA)

        stale_count = 0
        for row in rows:
            if row.source_session_id in active_ids:
                continue

            updated_at = _to_datetime(row.updated_at)
            if updated_at and updated_at > stale_threshold:
                continue

            payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
            payload["lifecycle"] = "stale"
            row.status = SessionStatus.ENDED
            row.ended_at = now
            row.raw_payload = payload
            stale_count += 1

        if stale_count:
            self.session_service.repository.db.commit()

        return stale_count

    def _normalize_media_path_for_local_fs(self, media_path: str | None) -> str | None:
        if not media_path:
            return None

        path = str(media_path).strip().replace("\\", "/")
        if not path:
            return None

        for source_prefix, target_prefix in self.path_mappings:
            source = source_prefix.rstrip("/")
            target = target_prefix.rstrip("/")
            if source and path.startswith(source):
                tail = path[len(source) :].lstrip("/")
                return f"{target}/{tail}" if tail else target

        roots = [root for root in self.poster_resolver.allowed_roots if root]
        for root in roots:
            root_posix = root.as_posix().rstrip("/")
            if root_posix and path.startswith(root_posix):
                return path

        for root in roots:
            root_posix = root.as_posix().rstrip("/")
            root_name = root.name.strip().lower()
            if not root_name:
                continue
            marker = f"/{root_name}/"
            idx = path.lower().find(marker)
            if idx >= 0:
                tail = path[idx + len(marker) :].lstrip("/")
                return f"{root_posix}/{tail}" if tail else root_posix

        return path

    @staticmethod
    def _looks_like_media_file(path: str) -> bool:
        normalized = path.strip().lower()
        return any(normalized.endswith(ext) for ext in _MEDIA_FILE_EXTENSIONS)

    @staticmethod
    def _parse_path_mappings(items: list[str]) -> list[tuple[str, str]]:
        parsed: list[tuple[str, str]] = []
        for raw in items:
            text = str(raw).strip()
            if not text:
                continue

            for separator in ("->", "=", ":"):
                if separator in text:
                    left, right = text.split(separator, 1)
                    source = left.strip().replace("\\", "/")
                    target = right.strip().replace("\\", "/")
                    if source and target:
                        parsed.append((source, target))
                    break

        return parsed


def _clean_display_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.replace("\ufffd", " ")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = " ".join(text.split())
    return text.strip()


def _episode_code(season_number: int | None, episode_number: int | None) -> str:
    if season_number is None and episode_number is None:
        return ""
    s = f"S{season_number:02d}" if season_number is not None else "S00"
    e = f"E{episode_number:02d}" if episode_number is not None else "E00"
    return f"{s}{e}"


def _strip_episode_prefixes(episode_text: str, series_text: str, code: str) -> str:
    value = episode_text
    if series_text and value.lower().startswith(series_text.lower()):
        value = value[len(series_text):].lstrip(" -:|.")
    if code and value.upper().startswith(code.upper()):
        value = value[len(code):].lstrip(" -:|.")
    if series_text and value.lower().startswith(series_text.lower()):
        value = value[len(series_text):].lstrip(" -:|.")
    return value.strip()


def _format_episode_title(series_title: str | None, episode_title: str | None, season_number: int | None, episode_number: int | None) -> str:
    clean_series = _clean_display_text(series_title)
    clean_episode = _clean_display_text(episode_title)
    code = _episode_code(season_number, episode_number)
    episode_only = _strip_episode_prefixes(clean_episode, clean_series, code) if clean_episode else ""

    parts: list[str] = []
    if clean_series:
        parts.append(clean_series)
    if code:
        parts.append(code)
    if episode_only and episode_only.lower() != clean_series.lower() and episode_only.upper() != code.upper():
        parts.append(episode_only)

    if parts:
        return " - ".join(parts)
    return episode_only or clean_episode or clean_series or "Untitled"


def _to_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if isinstance(value, (int, float)):
        if value > 1_000_000_000_000:
            return datetime.fromtimestamp(value / 1000.0, tz=UTC)
        return datetime.fromtimestamp(value, tz=UTC)
    return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _normalize_ip(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("[") and "]" in raw:
        return raw[1 : raw.find("]")]
    if raw.count(":") == 1 and raw.rsplit(":", 1)[1].isdigit():
        return raw.rsplit(":", 1)[0]
    return raw


def _format_bps(bps: int | None) -> str | None:
    if bps is None or bps <= 0:
        return None
    mbps = bps / 1_000_000
    if mbps >= 1:
        return f"{mbps:.1f} Mbps"
    return f"{(bps / 1000):.1f} Kbps"




