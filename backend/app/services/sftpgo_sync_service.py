from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.adapters.sftpgo.client import SFTPGoClient
from app.adapters.sftpgo.mapper import build_sftpgo_session_payload
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
from app.persistence.models.unified_stream_session import UnifiedStreamSessionModel
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

_DL_PATH_PATTERN = re.compile(r'dl:\s*"(?P<path>[^"]+)"', re.IGNORECASE)
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


class SFTPGoSyncService:
    def __init__(
        self,
        client: SFTPGoClient,
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
        self._last_sample: dict[str, tuple[int, datetime]] = {}
        self._active_session_ids_by_key: dict[str, str] = {}
        self._key_by_session_id: dict[str, str] = {}

    async def poll_once(self, log_limit: int = 200) -> dict[str, int]:
        self._rebuild_active_session_cache()
        cleaned_duplicate_active = self._collapse_duplicate_active_sessions()
        if cleaned_duplicate_active:
            self._rebuild_active_session_cache()

        active_connections = await self.client.fetch_active_connections()
        logs = await self.client.fetch_transfer_logs(limit=log_limit)

        download_logs = [log for log in logs if self._is_download_log(log)]
        log_index = self._index_logs(download_logs)
        grouped_connections = self._group_download_connections(active_connections, log_index)

        seen_ids: set[str] = set()
        imported = 0
        errors = 0

        for group in grouped_connections:
            try:
                key = group["logical_key"]
                source_session_id = self._resolve_session_id_for_key(key)
                if not source_session_id:
                    errors += 1
                    continue

                seen_ids.add(source_session_id)
                connection = dict(group["connection"])
                related_logs = group["logs"]

                media_path = self._normalize_media_path_for_local_fs(group["file_path"])
                if not media_path or not self._looks_like_media_file(media_path):
                    continue

                connection["file_path"] = media_path
                connection["streamfuse_logical_key"] = key

                bandwidth_bps = self._estimate_bandwidth_bps(
                    source_session_id,
                    connection,
                    related_logs,
                )
                media_info = parse_mediainfo_for_media(media_path)
                poster = self.poster_resolver.resolve(media_path, None)

                payload = build_sftpgo_session_payload(
                    source_session_id=source_session_id,
                    connection=connection,
                    related_logs=related_logs,
                    status=SessionStatus.ACTIVE,
                    bandwidth_bps=bandwidth_bps,
                    poster_path=str(poster),
                    media_info=media_info,
                )
                self.session_service.create_session(payload)
                imported += 1
            except Exception:
                errors += 1
                logger.exception("Failed to map/store SFTPGo payload")

        cleaned_invalid = self._cleanup_invalid_active_sessions(seen_ids)
        cleaned_history_noise = self._purge_invalid_history_noise()
        stale_marked = self._mark_stale_sessions(seen_ids)

        self._rebuild_active_session_cache()

        return {
            "active_imported": imported,
            "cleaned_duplicate_active": cleaned_duplicate_active,
            "cleaned_invalid": cleaned_invalid,
            "cleaned_history_noise": cleaned_history_noise,
            "stale_marked": stale_marked,
            "errors": errors,
            "total_processed": imported + cleaned_duplicate_active + cleaned_invalid + cleaned_history_noise + stale_marked,
        }

    def _group_download_connections(
        self,
        active_connections: list[dict[str, Any]],
        log_index: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}

        for connection in active_connections:
            if not self._is_download_connection(connection):
                continue

            related_logs = self._correlate_logs(connection, log_index)

            media_path = self._resolve_file_path(connection, related_logs)
            if not media_path or not self._looks_like_media_file(media_path):
                continue

            if not self._looks_like_download(connection, related_logs):
                continue

            username = str(
                connection.get("username")
                or _best_log_field(related_logs, "username")
                or "unknown"
            )
            if not username.strip():
                continue

            ip_value = str(
                connection.get("ip_address")
                or connection.get("remote_address")
                or _best_log_field(related_logs, "ip_address")
                or _best_log_field(related_logs, "remote_addr")
                or ""
            )
            normalized_ip = self._normalize_ip(ip_value)
            if not normalized_ip:
                continue

            logical_key = self._group_key(username, normalized_ip, media_path)

            current = grouped.get(logical_key)
            if current is None:
                grouped[logical_key] = {
                    "logical_key": logical_key,
                    "file_path": media_path,
                    "logs": list(related_logs),
                    "connection": self._connection_snapshot(connection, media_path, normalized_ip),
                }
                continue

            current["logs"].extend(related_logs)
            current["connection"] = self._merge_connections(
                current["connection"],
                connection,
                media_path,
                normalized_ip,
            )

        return list(grouped.values())

    def _collapse_duplicate_active_sessions(self) -> int:
        rows = self.session_service.repository.list_active_by_source(StreamSource.SFTPGO)
        grouped: dict[str, list[UnifiedStreamSessionModel]] = defaultdict(list)

        for row in rows:
            key = self._logical_key_for_row(row)
            if not key:
                continue
            grouped[key].append(row)

        removed = 0
        for dup_rows in grouped.values():
            if len(dup_rows) < 2:
                continue

            sorted_rows = sorted(
                dup_rows,
                key=lambda item: (_as_utc(item.updated_at) or datetime.min.replace(tzinfo=UTC), item.id),
                reverse=True,
            )
            keep = sorted_rows[0]
            keep_key = self._logical_key_for_row(keep)

            for stale in sorted_rows[1:]:
                self.session_service.repository.db.delete(stale)
                self._drop_session_from_caches(stale.source_session_id)
                removed += 1

            if keep_key:
                self._active_session_ids_by_key[keep_key] = keep.source_session_id
                self._key_by_session_id[keep.source_session_id] = keep_key

        if removed:
            self.session_service.repository.db.commit()

        return removed

    def _logical_key_for_row(self, row: UnifiedStreamSessionModel) -> str:
        raw_payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
        connection = raw_payload.get("connection") if isinstance(raw_payload.get("connection"), dict) else {}
        cached_key = str(connection.get("streamfuse_logical_key") or "").strip()
        if cached_key:
            return cached_key

        file_path = (row.file_path or "").strip()
        user_name = (row.user_name or "").strip()
        if not file_path or not user_name:
            return ""

        ip_value = str(
            row.ip_address
            or connection.get("ip_address")
            or connection.get("remote_address")
            or ""
        )
        normalized_ip = self._normalize_ip(ip_value)
        if not normalized_ip:
            return ""

        return self._group_key(user_name, normalized_ip, file_path)

    def _cleanup_invalid_active_sessions(self, active_ids: set[str]) -> int:
        rows = self.session_service.repository.list_active_by_source(StreamSource.SFTPGO)
        pruned = 0

        for row in rows:
            if row.source_session_id in active_ids:
                continue

            file_path = (row.file_path or "").strip()
            if file_path and self._looks_like_media_file(file_path):
                continue

            self.session_service.repository.db.delete(row)
            self._drop_session_from_caches(row.source_session_id)
            pruned += 1

        if pruned:
            self.session_service.repository.db.commit()

        return pruned

    def _purge_invalid_history_noise(self) -> int:
        stmt = select(UnifiedStreamSessionModel).where(
            UnifiedStreamSessionModel.source == StreamSource.SFTPGO,
            UnifiedStreamSessionModel.status != SessionStatus.ACTIVE,
        )
        rows = list(self.session_service.repository.db.scalars(stmt).all())
        removed = 0

        for row in rows:
            file_path = (row.file_path or "").strip()
            title = (row.title or "").strip().lower()
            is_noise_title = title.startswith("ftp ") or title == "n/a" or title == ""
            is_media = bool(file_path and self._looks_like_media_file(file_path))
            if is_media and not is_noise_title:
                continue

            self.session_service.repository.db.delete(row)
            self._drop_session_from_caches(row.source_session_id)
            removed += 1

        if removed:
            self.session_service.repository.db.commit()

        return removed

    def _mark_stale_sessions(self, active_ids: set[str]) -> int:
        now = datetime.now(UTC)
        stale_threshold = now - timedelta(seconds=self.stale_seconds)

        rows = self.session_service.repository.list_active_by_source(StreamSource.SFTPGO)
        stale_count = 0

        for row in rows:
            if row.source_session_id in active_ids:
                continue

            updated_at = _as_utc(row.updated_at)
            if updated_at and updated_at > stale_threshold:
                continue

            payload = row.raw_payload if isinstance(row.raw_payload, dict) else {}
            payload["lifecycle"] = "stale"
            row.status = SessionStatus.ENDED
            row.ended_at = now
            row.raw_payload = payload
            self._drop_session_from_caches(row.source_session_id)
            stale_count += 1

        if stale_count:
            self.session_service.repository.db.commit()

        return stale_count

    def _rebuild_active_session_cache(self) -> None:
        self._active_session_ids_by_key = {}
        self._key_by_session_id = {}

        rows = self.session_service.repository.list_active_by_source(StreamSource.SFTPGO)
        for row in rows:
            logical_key = self._logical_key_for_row(row)
            if not logical_key:
                continue

            self._active_session_ids_by_key[logical_key] = row.source_session_id
            self._key_by_session_id[row.source_session_id] = logical_key

    def _resolve_session_id_for_key(self, logical_key: str) -> str:
        existing = self._active_session_ids_by_key.get(logical_key)
        if existing:
            return existing

        stamp = int(datetime.now(UTC).timestamp() * 1000)
        slug = abs(hash(logical_key))
        source_session_id = f"sftpgo-{slug}-{stamp}"
        self._active_session_ids_by_key[logical_key] = source_session_id
        self._key_by_session_id[source_session_id] = logical_key
        return source_session_id

    def _drop_session_from_caches(self, source_session_id: str) -> None:
        logical_key = self._key_by_session_id.pop(source_session_id, None)
        if not logical_key:
            return

        current = self._active_session_ids_by_key.get(logical_key)
        if current == source_session_id:
            self._active_session_ids_by_key.pop(logical_key, None)

    def _index_logs(self, logs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        by_conn: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for log in logs:
            conn_id = str(log.get("connection_id") or log.get("session_id") or "").strip()
            if conn_id:
                by_conn[conn_id].append(log)
        return by_conn

    def _correlate_logs(
        self,
        connection: dict[str, Any],
        log_index: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        conn_id = str(connection.get("connection_id") or connection.get("id") or "").strip()
        if conn_id and conn_id in log_index:
            return log_index[conn_id]

        username = str(connection.get("username") or "")
        ip_addr = self._normalize_ip(
            str(connection.get("ip_address") or connection.get("remote_address") or "")
        )
        path = str(
            connection.get("file_path")
            or connection.get("path")
            or connection.get("current_path")
            or ""
        )

        correlated: list[dict[str, Any]] = []
        for logs in log_index.values():
            for log in logs:
                if username and str(log.get("username") or "") != username:
                    continue
                log_ip = self._normalize_ip(
                    str(
                        log.get("ip_address")
                        or log.get("remote_addr")
                        or log.get("remote_address")
                        or ""
                    )
                )
                if ip_addr and log_ip and log_ip != ip_addr:
                    continue
                log_path = str(log.get("file_path") or log.get("path") or "")
                if path and log_path and log_path != path:
                    continue
                correlated.append(log)
        return correlated

    def _estimate_bandwidth_bps(
        self,
        session_id: str,
        connection: dict[str, Any],
        logs: list[dict[str, Any]],
    ) -> int | None:
        now = datetime.now(UTC)
        bytes_now = self._extract_total_bytes(connection, logs)
        if bytes_now is None:
            return None

        prev = self._last_sample.get(session_id)
        self._last_sample[session_id] = (bytes_now, now)
        if prev is None:
            return None

        prev_bytes, prev_ts = prev
        delta_bytes = bytes_now - prev_bytes
        delta_seconds = (now - prev_ts).total_seconds()

        if delta_bytes <= 0 or delta_seconds <= 0:
            return None

        return int(delta_bytes / delta_seconds)

    @staticmethod
    def _extract_total_bytes(connection: dict[str, Any], logs: list[dict[str, Any]]) -> int | None:
        conn_bytes_sent = _to_int(connection.get("bytes_sent"))
        conn_bytes_received = _to_int(connection.get("bytes_received"))
        conn_total = None
        if conn_bytes_sent is not None or conn_bytes_received is not None:
            conn_total = (conn_bytes_sent or 0) + (conn_bytes_received or 0)

        log_total = None
        for log in reversed(logs):
            bytes_total = _to_int(log.get("bytes_total"))
            if bytes_total is not None:
                log_total = bytes_total
                break
            sent = _to_int(log.get("bytes_sent"))
            recv = _to_int(log.get("bytes_received"))
            if sent is not None or recv is not None:
                log_total = (sent or 0) + (recv or 0)
                break

        return conn_total if conn_total is not None else log_total

    @staticmethod
    def _resolve_file_path(connection: dict[str, Any], logs: list[dict[str, Any]]) -> str | None:
        path = connection.get("file_path") or connection.get("path") or connection.get("current_path")
        if path:
            return str(path)

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            for transfer in transfers:
                if not isinstance(transfer, dict):
                    continue
                candidate = transfer.get("path") or transfer.get("file_path")
                if candidate:
                    return str(candidate)

        for log in reversed(logs):
            value = log.get("file_path") or log.get("path")
            if value:
                return str(value)
            info = str(log.get("info") or "")
            extracted = _extract_path_from_info(info)
            if extracted:
                return extracted

        info = str(connection.get("info") or "")
        return _extract_path_from_info(info)

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
    def _normalize_ip(value: str) -> str:
        raw = value.strip()
        if not raw:
            return ""

        if raw.startswith("[") and "]" in raw:
            bracket_end = raw.find("]")
            return raw[1:bracket_end]

        if raw.count(":") == 1 and raw.rsplit(":", 1)[1].isdigit():
            return raw.rsplit(":", 1)[0]

        return raw

    @staticmethod
    def _group_key(username: str, ip_address: str, file_path: str) -> str:
        return f"{username.strip().lower()}|{ip_address.strip()}|{file_path.strip().lower()}"

    def _looks_like_download(self, connection: dict[str, Any], logs: list[dict[str, Any]]) -> bool:
        if any(self._is_download_log(log) for log in logs):
            return True

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            for transfer in transfers:
                if not isinstance(transfer, dict):
                    continue
                op = str(transfer.get("operation_type") or "").lower()
                if op == "download":
                    return True

        info = str(connection.get("info") or "").lower()
        if "dl:" in info or "download" in info:
            return True

        return False

    @staticmethod
    def _is_download_connection(connection: dict[str, Any]) -> bool:
        command = str(connection.get("command") or "").upper()
        if command == "RETR":
            return True

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            if any(
                isinstance(transfer, dict)
                and str(transfer.get("operation_type") or "").lower() == "download"
                for transfer in transfers
            ):
                return True

        info = str(connection.get("info") or "").lower()
        if "dl:" in info or "download" in info:
            return True

        file_path = connection.get("file_path") or connection.get("path") or connection.get("current_path")
        bytes_sent = _to_int(connection.get("bytes_sent")) or 0
        if file_path and bytes_sent > 0:
            return True

        return False

    def _connection_snapshot(
        self,
        connection: dict[str, Any],
        media_path: str,
        normalized_ip: str,
    ) -> dict[str, Any]:
        snapshot = dict(connection)
        snapshot["file_path"] = media_path
        if normalized_ip:
            snapshot["ip_address"] = normalized_ip
        return snapshot

    def _merge_connections(
        self,
        current: dict[str, Any],
        incoming: dict[str, Any],
        media_path: str,
        normalized_ip: str,
    ) -> dict[str, Any]:
        merged = dict(current)

        current_last = _to_int(current.get("last_activity")) or 0
        incoming_last = _to_int(incoming.get("last_activity")) or 0
        if incoming_last >= current_last:
            merged.update(incoming)

        merged["file_path"] = media_path
        if normalized_ip:
            merged["ip_address"] = normalized_ip

        sent_total = (_to_int(current.get("bytes_sent")) or 0) + (
            _to_int(incoming.get("bytes_sent")) or 0
        )
        recv_total = (_to_int(current.get("bytes_received")) or 0) + (
            _to_int(incoming.get("bytes_received")) or 0
        )
        merged["bytes_sent"] = sent_total
        merged["bytes_received"] = recv_total
        return merged

    @staticmethod
    def _is_download_log(log: dict[str, Any]) -> bool:
        event = str(log.get("event") or log.get("operation") or log.get("action") or "").lower()
        direction = str(log.get("direction") or "").lower()
        info = str(log.get("info") or "").lower()

        if direction in {"download", "dl", "out"}:
            return True
        if any(token in event for token in ("download", "dl")):
            return True
        if "dl:" in info or "download" in info:
            return True
        return False

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


def _extract_path_from_info(info: str) -> str | None:
    if not info:
        return None
    match = _DL_PATH_PATTERN.search(info)
    if not match:
        return None
    return match.group("path")


def _best_log_field(logs: list[dict[str, Any]], field: str) -> Any:
    for item in reversed(logs):
        value = item.get(field)
        if value not in (None, ""):
            return value
    return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)





