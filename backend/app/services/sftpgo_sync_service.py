from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.adapters.sftpgo.client import SFTPGoClient
from app.adapters.sftpgo.mapper import build_sftpgo_session_payload
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
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
    ".wmv",
    ".flv",
    ".webm",
    ".iso",
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

    async def poll_once(self, log_limit: int = 200) -> dict[str, int]:
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
                source_session_id = group["source_session_id"]
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

        stale_marked = self._mark_stale_sessions(seen_ids)

        return {
            "active_imported": imported,
            "stale_marked": stale_marked,
            "errors": errors,
            "total_processed": imported + stale_marked,
        }

    def _group_download_connections(
        self,
        active_connections: list[dict[str, Any]],
        log_index: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}

        for connection in active_connections:
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
            ip_value = str(
                connection.get("ip_address")
                or connection.get("remote_address")
                or _best_log_field(related_logs, "ip_address")
                or _best_log_field(related_logs, "remote_addr")
                or ""
            )
            normalized_ip = self._normalize_ip(ip_value)
            key = self._group_key(username, normalized_ip, media_path)

            current = grouped.get(key)
            if current is None:
                source_session_id = self._aggregate_session_id(username, normalized_ip, media_path)
                grouped[key] = {
                    "source_session_id": source_session_id,
                    "file_path": media_path,
                    "logs": list(related_logs),
                    "connection": self._connection_snapshot(
                        connection,
                        media_path,
                        normalized_ip,
                    ),
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
            stale_count += 1

        if stale_count:
            self.session_service.repository.db.commit()

        return stale_count

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

        # 1) Explicit admin mappings from settings UI.
        for source_prefix, target_prefix in self.path_mappings:
            source = source_prefix.rstrip("/")
            target = target_prefix.rstrip("/")
            if source and path.startswith(source):
                tail = path[len(source) :].lstrip("/")
                return f"{target}/{tail}" if tail else target

        # 2) Already mapped to allowed roots.
        roots = [root for root in self.poster_resolver.allowed_roots if root]
        for root in roots:
            root_posix = root.as_posix().rstrip("/")
            if root_posix and path.startswith(root_posix):
                return path

        # 3) Suffix mapping by root folder name (peliculas/series).
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

    @staticmethod
    def _aggregate_session_id(username: str, ip_address: str, file_path: str) -> str:
        user = username.strip().lower() or "unknown"
        ip = ip_address.strip() or "unknown"
        path = file_path.strip().lower().replace(" ", "_")
        return f"sftpgo-{user}-{ip}-{path}"

    def _looks_like_download(self, connection: dict[str, Any], logs: list[dict[str, Any]]) -> bool:
        if any(self._is_download_log(log) for log in logs):
            return True

        info = str(connection.get("info") or "").lower()
        return bool("dl:" in info or "download" in info)

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

