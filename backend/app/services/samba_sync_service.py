from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.adapters.samba.client import SambaClient
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.media_parser import clean_movie_title, detect_media_type, parse_series_context
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService

# Sessions for the same user+file that ended less than this many seconds ago
# are considered the same sitting and will be reused (merged) rather than
# creating a new history entry.  Sessions ended longer ago are treated as a
# fresh re-watch and will produce a separate history entry.
_SAME_SESSION_MERGE_WINDOW_SECONDS = 3600  # 1 hour

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
    KEY_SAMBA_POLL_COUNTS = "samba_poll_counts"

    def __init__(
        self,
        client: SambaClient,
        session_service: SessionService,
        poster_resolver: PosterResolver,
        stale_seconds: int = 90,
        path_mappings: list[str] | None = None,
        min_consecutive_polls_for_active: int = 2,
        min_open_seconds_for_active: int = 20,
        app_setting_repository: AppSettingRepository | None = None,
    ) -> None:
        self.client = client
        self.session_service = session_service
        self.poster_resolver = poster_resolver
        self.stale_seconds = stale_seconds
        self.path_mappings = self._parse_path_mappings(path_mappings or [])
        self.min_consecutive_polls_for_active = max(1, int(min_consecutive_polls_for_active))
        self.min_open_seconds_for_active = max(0, int(min_open_seconds_for_active))
        self.app_setting_repository = app_setting_repository
        self._active_session_ids_by_key: dict[str, str] = {}
        self._seen_poll_counts: dict[str, int] = self._load_seen_poll_counts()
        self._key_by_session_id: dict[str, str] = {}

    async def poll_once(self) -> dict[str, int]:
        self._rebuild_active_session_cache()
        cleaned_duplicate_active = self._collapse_duplicate_active_sessions()
        if cleaned_duplicate_active:
            self._rebuild_active_session_cache()

        connections = await self.client.fetch_active_connections()
        grouped = self._group_download_connections(connections)

        seen_ids: set[str] = set()
        imported = 0
        errors = 0

        current_keys = {
            str(item.get("logical_key") or "")
            for item in grouped
            if str(item.get("logical_key") or "")
        }
        next_counts: dict[str, int] = {}
        for key in current_keys:
            next_counts[key] = self._seen_poll_counts.get(key, 0) + 1
        self._seen_poll_counts = next_counts
        self._persist_seen_poll_counts()

        for item in grouped:
            try:
                logical_key = str(item.get("logical_key") or "")
                if not logical_key:
                    continue
                seen_count = self._seen_poll_counts.get(logical_key, 0)
                if seen_count < self.min_consecutive_polls_for_active:
                    continue

                media_path = self._normalize_media_path_for_local_fs(item["file_path"])
                if not media_path or not self._looks_like_media_file(media_path):
                    continue

                user_name = str(item["connection"].get("username") or "unknown")
                ip_value = _normalize_ip(str(item["connection"].get("remote_address") or ""))
                logical_key = logical_key or self._group_key(user_name, ip_value, media_path)
                source_session_id = self._resolve_session_id_for_key(
                    logical_key,
                    user_name=user_name,
                    file_path=media_path,
                )
                seen_ids.add(source_session_id)

                media_info = parse_mediainfo_for_media(media_path)
                poster = self.poster_resolver.resolve(media_path, None)
                series_ctx = parse_series_context(media_path)
                media_type = detect_media_type(media_path)
                file_name = Path(media_path).name

                series_title = _clean_display_text(str(series_ctx.get("series_title") or "")) or None
                season_number = series_ctx.get("season_number")
                episode_number = series_ctx.get("episode_number")

                if media_info and media_info.series_title:
                    series_title = _clean_display_text(media_info.series_title) or series_title
                if media_info and media_info.season_number is not None:
                    season_number = media_info.season_number
                if media_info and media_info.episode_number is not None:
                    episode_number = media_info.episode_number

                media_title = _clean_display_text(media_info.episode_title if media_info and media_info.episode_title else media_info.title) if media_info and (media_info.episode_title or media_info.title) else ""
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
                open_age_seconds = max(0.0, (datetime.now(UTC) - started_at).total_seconds())
                if open_age_seconds < self.min_open_seconds_for_active:
                    continue

                bandwidth_bps = (
                    (media_info.overall_bitrate_bps or media_info.video_bitrate_bps)
                    if media_info is not None
                    else None
                )

                payload = UnifiedStreamSessionCreate(
                    source=StreamSource.SAMBA,
                    source_session_id=source_session_id,
                    status=SessionStatus.ACTIVE,
                    user_name=user_name,
                    ip_address=ip_value or None,
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
            "cleaned_duplicate_active": cleaned_duplicate_active,
            "stale_marked": stale_marked,
            "errors": errors,
            "total_processed": imported + cleaned_duplicate_active + stale_marked,
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

                key = self._group_key(username, ip_value, file_path)
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

        # Samba directory scanners can momentarily open many media files.
        # Keep one strongest candidate per user+ip per poll to avoid floods.
        by_viewer: dict[str, dict[str, Any]] = {}
        for candidate in grouped.values():
            conn = candidate.get("connection") if isinstance(candidate.get("connection"), dict) else {}
            transfer = candidate.get("transfer") if isinstance(candidate.get("transfer"), dict) else {}
            username = str(conn.get("username") or "").strip().lower()
            ip_value = _normalize_ip(str(conn.get("remote_address") or ""))
            viewer_key = f"{username}|{ip_value}"

            current = by_viewer.get(viewer_key)
            if current is None:
                by_viewer[viewer_key] = candidate
                continue

            current_transfer = current.get("transfer") if isinstance(current.get("transfer"), dict) else {}
            current_size = _to_int(current_transfer.get("size")) or 0
            candidate_size = _to_int(transfer.get("size")) or 0
            if candidate_size > current_size:
                by_viewer[viewer_key] = candidate
                continue
            if candidate_size < current_size:
                continue

            current_started = _to_datetime(current_transfer.get("start_time"))
            candidate_started = _to_datetime(transfer.get("start_time"))
            if candidate_started and (current_started is None or candidate_started < current_started):
                by_viewer[viewer_key] = candidate

        return list(by_viewer.values())

    def _collapse_duplicate_active_sessions(self) -> int:
        rows = self.session_service.repository.list_active_by_source(StreamSource.SAMBA)
        grouped: dict[str, list[UnifiedStreamSessionModel]] = {}

        for row in rows:
            key = self._logical_key_for_row(row)
            if not key:
                continue
            grouped.setdefault(key, []).append(row)

        removed = 0
        for dup_rows in grouped.values():
            if len(dup_rows) < 2:
                continue

            sorted_rows = sorted(
                dup_rows,
                key=lambda item: (_to_datetime(item.updated_at) or datetime.min.replace(tzinfo=UTC), item.id),
                reverse=True,
            )
            keep = sorted_rows[0]

            for stale in sorted_rows[1:]:
                self.session_service.repository.db.delete(stale)
                removed += 1

            keep_key = self._logical_key_for_row(keep)
            if keep_key:
                self._active_session_ids_by_key[keep_key] = keep.source_session_id
                self._key_by_session_id[keep.source_session_id] = keep_key

        if removed:
            self.session_service.repository.db.commit()

        return removed

    def _logical_key_for_row(self, row: UnifiedStreamSessionModel) -> str:
        file_path = (row.file_path or "").strip()
        user_name = (row.user_name or "").strip()
        ip_value = _normalize_ip(row.ip_address or "")
        if not file_path or not user_name:
            return ""
        return self._group_key(user_name, ip_value, file_path)

    def _rebuild_active_session_cache(self) -> None:
        self._active_session_ids_by_key = {}
        self._key_by_session_id = {}

        rows = self.session_service.repository.list_active_by_source(StreamSource.SAMBA)
        for row in rows:
            key = self._logical_key_for_row(row)
            if not key:
                continue
            self._active_session_ids_by_key[key] = row.source_session_id
            self._key_by_session_id[row.source_session_id] = key

    def _resolve_session_id_for_key(
        self,
        logical_key: str,
        user_name: str = "",
        file_path: str = "",
    ) -> str:
        # 1. Already in active cache — reuse.
        existing = self._active_session_ids_by_key.get(logical_key)
        if existing:
            return existing

        # 2. Look for a recently-ended session (same user + file, within merge
        #    window) so that brief pauses / connection drops are merged into the
        #    same sitting rather than creating duplicate history entries.
        #    Sessions that ended longer ago (e.g. days) are treated as a fresh
        #    re-watch and fall through to a new session_id below.
        if user_name and file_path:
            recent = self.session_service.repository.find_recent_ended_by_user_and_file(
                source=StreamSource.SAMBA,
                user_name=user_name,
                file_path=file_path,
                within_seconds=_SAME_SESSION_MERGE_WINDOW_SECONDS,
            )
            if recent:
                source_session_id = recent.source_session_id
                self._active_session_ids_by_key[logical_key] = source_session_id
                self._key_by_session_id[source_session_id] = logical_key
                return source_session_id

        # 3. Genuinely new session (first watch, or re-watch days later).
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

            # Remove from in-memory caches so that a future re-watch of the
            # same file by the same user creates a brand-new session instead
            # of updating this now-ended one.
            logical_key = self._key_by_session_id.pop(row.source_session_id, None)
            if logical_key:
                self._active_session_ids_by_key.pop(logical_key, None)

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
    def _group_key(username: str, ip_value: str, file_path: str) -> str:
        return f"{username.strip().lower()}|{_normalize_ip(ip_value)}|{file_path.strip().lower()}"

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


    def _load_seen_poll_counts(self) -> dict[str, int]:
        if self.app_setting_repository is None:
            return {}
        row = self.app_setting_repository.get(self.KEY_SAMBA_POLL_COUNTS)
        if row is None or not row.value:
            return {}
        try:
            parsed = json.loads(row.value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, int] = {}
        for key, value in parsed.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                continue
            if numeric > 0:
                result[normalized_key] = numeric
        return result

    def _persist_seen_poll_counts(self) -> None:
        if self.app_setting_repository is None:
            return
        payload = json.dumps(self._seen_poll_counts, ensure_ascii=False, separators=(",", ":"))
        self.app_setting_repository.set(
            self.KEY_SAMBA_POLL_COUNTS,
            payload,
            "Internal Samba logical-key poll counters",
        )
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
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.isdigit():
            value = int(raw)
        else:
            try:
                iso = raw.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(iso)
                return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return None
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





