from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.adapters.sftpgo.client import SFTPGoClient
from app.adapters.sftpgo.log_parser import trim_transfer_log_file
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
_MIN_MEANINGFUL_TRANSFER_BYTES = 50 * 1024 * 1024   # active connection must have sent ≥ 50 MB → real playback
_MIN_SEGMENT_BYTES_FOR_PLAYBACK = 50 * 1024 * 1024  # single completed segment ≥ 50 MB → real playback
# Sessions younger than this that go stale are library-scan pre-buffers, not real watches.
# Infuse disconnects in < 5 s when browsing; real playback lasts minutes.
_MIN_SESSION_DURATION_SECONDS = 60
# When a user's router has a NAT timeout (~120 s is common), Infuse reconnects every 2 minutes.
# Each individual FTP segment is small (< 50 MB) but the cumulative total across all reconnects
# proves real playback.  We aggregate completed log entries within this window before deciding.
_RECONNECT_AGGREGATE_WINDOW_SECONDS = 30 * 60  # 30-minute rolling window
# Log-only session creation: minimum number of completed segments OR minimum
# cumulative elapsed transfer time to distinguish a real download/stream from
# a brief Infuse library-scan probe (which typically generates 2-5 small segments
# completing in under a second each).
_LOG_ONLY_MIN_SEGMENTS = 5        # at least 5 completed RETR operations, OR …
_LOG_ONLY_MIN_ELAPSED_MS = 60_000 # … at least 60 s of cumulative transfer time


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
        self._last_log_trim: datetime = datetime.min.replace(tzinfo=UTC)
        self._log_trim_interval_hours: int = 1
        self._log_max_age_days: int = 2
        # Drop entries smaller than 1 MB during trim — these are thumbnail fetches,
        # metadata probes and format-detection range-requests from clients like Infuse.
        # They represent the bulk of log volume (hundreds of thousands per day) but
        # are irrelevant for session detection which requires ≥ 50 MB transfers.
        self._log_min_size_bytes: int = 1 * 1024 * 1024

    async def poll_once(self, log_limit: int = 200) -> dict[str, int]:
        self._maybe_trim_log_file()
        self._rebuild_active_session_cache()
        cleaned_duplicate_active = self._collapse_duplicate_active_sessions()
        if cleaned_duplicate_active:
            self._rebuild_active_session_cache()

        active_connections = await self.client.fetch_active_connections()
        logs = await self.client.fetch_transfer_logs(limit=log_limit)

        download_logs = [log for log in logs if self._is_download_log(log)]
        log_index = self._index_logs(download_logs)
        grouped_connections = self._group_download_connections(active_connections, log_index, download_logs)

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

                media_info = parse_mediainfo_for_media(media_path)
                mediainfo_bps = (
                    (media_info.overall_bitrate_bps or media_info.video_bitrate_bps)
                    if media_info is not None
                    else None
                )
                # Use actual delta-bytes/delta-time between polls when available;
                # fall back to the file's encoded bitrate on the first poll.
                live_bps = self._estimate_bandwidth_bps(source_session_id, connection, related_logs)
                bandwidth_bps = live_bps if live_bps is not None else mediainfo_bps
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

        # Rebuild cache before log-only pass so the has_active check is fresh.
        self._rebuild_active_session_cache()

        # Detect completed downloads that finished entirely between two polls
        # (e.g. parallel offline downloads at full network speed).  Must run after
        # the cache rebuild so we correctly skip user+file combos already tracked
        # by an active session.
        log_only_imported = self._import_completed_log_sessions(download_logs)

        return {
            "active_imported": imported,
            "log_only_imported": log_only_imported,
            "cleaned_duplicate_active": cleaned_duplicate_active,
            "cleaned_invalid": cleaned_invalid,
            "cleaned_history_noise": cleaned_history_noise,
            "stale_marked": stale_marked,
            "errors": errors,
            "total_processed": imported + log_only_imported + cleaned_duplicate_active + cleaned_invalid + cleaned_history_noise + stale_marked,
        }

    def _group_download_connections(
        self,
        active_connections: list[dict[str, Any]],
        log_index: dict[str, list[dict[str, Any]]],
        all_download_logs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}

        for connection in active_connections:
            if not self._is_download_connection(connection):
                continue

            related_logs = self._correlate_logs(connection, log_index)

            media_path = self._resolve_file_path(connection, related_logs)
            if not media_path or not self._looks_like_media_file(media_path):
                continue

            # Extract username here (before _looks_like_download) so we can pass it
            # for NAT-reconnect cumulative-bytes aggregation.
            username = str(
                connection.get("username")
                or _best_log_field(related_logs, "username")
                or "unknown"
            )
            if not username.strip():
                continue

            if not self._looks_like_download(
                connection,
                related_logs,
                all_download_logs=all_download_logs,
                username=username,
                file_path=media_path,
            ):
                continue

            ip_value = str(
                connection.get("ip_address")
                or connection.get("remote_address")
                or connection.get("ip")  # SFTPGo API v2 uses "ip" (format "host:port")
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
                # Log-only sessions (parallel offline downloads) are written as
                # ENDED from the start and have started_at ≈ ended_at because
                # all parallel segments finish within seconds.  They are already
                # validated by the _LOG_ONLY_MIN_SEGMENTS / _LOG_ONLY_MIN_ELAPSED_MS
                # filters, so the short-duration heuristic below does not apply.
                if str(row.source_session_id or "").startswith("sftpgo-log-"):
                    continue

                # Also purge real-media entries that are suspiciously short-lived —
                # these are FTP library-scan pre-buffers that slipped through the
                # _MIN_MEANINGFUL_TRANSFER_BYTES gate before it was raised to 50 MB.
                started = _as_utc(row.started_at)
                ended = _as_utc(row.ended_at) or _as_utc(row.updated_at)
                if started and ended:
                    duration_s = (ended - started).total_seconds()
                    if duration_s < _MIN_SESSION_DURATION_SECONDS:
                        logger.debug(
                            "Purging short history entry %s (%.0f s) — likely library scan",
                            row.source_session_id,
                            duration_s,
                        )
                        # fall through to delete below
                    else:
                        continue
                else:
                    continue  # no timestamps → keep

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

            # Treat NULL updated_at as "just updated now" — a freshly-created session
            # that hasn't been touched yet should not be immediately marked stale.
            updated_at = _as_utc(row.updated_at) or now
            if updated_at > stale_threshold:
                continue

            # Sessions that existed for less than _MIN_SESSION_DURATION_SECONDS are
            # almost certainly Infuse/FTP library-scan pre-buffers, not real watches.
            # Browsing a media library opens a file, downloads ~10-26 MB and disconnects
            # within seconds.  Delete these silently instead of surfacing them in history.
            started_at = _as_utc(row.started_at) or updated_at
            session_age_seconds = (updated_at - started_at).total_seconds()
            if session_age_seconds < _MIN_SESSION_DURATION_SECONDS:
                logger.debug(
                    "Deleting short-lived SFTPGo session %s (%.0f s) — likely library scan",
                    row.source_session_id,
                    session_age_seconds,
                )
                self.session_service.repository.db.delete(row)
                self._drop_session_from_caches(row.source_session_id)
                stale_count += 1
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

    def _maybe_trim_log_file(self) -> None:
        """Trim the transfer log file at most once per hour.

        Removes entries that are either:
        - older than *_log_max_age_days* (default 2 days), OR
        - smaller than *_log_min_size_bytes* (default 1 MB).

        The size filter alone eliminates ~95 % of log volume: FTP clients like
        Infuse generate hundreds of tiny range-requests per day for thumbnail
        fetching, metadata probing and format detection.  StreamFuse only cares
        about large completed transfers (≥ 50 MB) for session correlation.
        """
        now = datetime.now(UTC)
        hours_since_trim = (now - self._last_log_trim).total_seconds() / 3600
        if hours_since_trim < self._log_trim_interval_hours:
            return

        log_path: str | None = getattr(self.client.provider, "transfer_log_json_path", None)
        if not log_path:
            return

        try:
            removed = trim_transfer_log_file(
                log_path,
                max_age_days=self._log_max_age_days,
                min_size_bytes=self._log_min_size_bytes,
            )
            if removed:
                logger.info(
                    "SFTPGo log trim: removed %d entries (age>%dd or size<%dB) from %s",
                    removed, self._log_max_age_days, self._log_min_size_bytes, log_path,
                )
        except Exception:
            logger.exception("SFTPGo log trim failed")
        finally:
            self._last_log_trim = now

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

        raw_bps = int(delta_bytes / delta_seconds)
        # Cap at 1 Gbps. active_transfers[].size can report the total file size in some
        # SFTPGo versions, causing a massive delta on the first poll that inflates bandwidth.
        return min(raw_bps, 1_000_000_000)

    @staticmethod
    def _extract_total_bytes(connection: dict[str, Any], logs: list[dict[str, Any]]) -> int | None:
        conn_bytes_sent = _to_int(connection.get("bytes_sent"))
        conn_bytes_received = _to_int(connection.get("bytes_received"))
        conn_total = None
        if conn_bytes_sent is not None or conn_bytes_received is not None:
            conn_total = (conn_bytes_sent or 0) + (conn_bytes_received or 0)

        # SFTPGo API v2: bytes in progress are stored per-transfer as "size"
        if conn_total is None:
            transfer_bytes = 0
            transfers = connection.get("active_transfers")
            if isinstance(transfers, list):
                for transfer in transfers:
                    if isinstance(transfer, dict):
                        transfer_bytes += _to_int(transfer.get("size")) or 0
            if transfer_bytes > 0:
                conn_total = transfer_bytes

        log_total = None
        for log in reversed(logs):
            bytes_total = _to_int(log.get("bytes_total"))
            if bytes_total is not None:
                log_total = bytes_total
                break
            sent = _to_int(log.get("bytes_sent"))
            recv = _to_int(log.get("bytes_received"))
            # SFTPGo FTP log format uses "size_bytes" for completed transfer size
            size = _to_int(log.get("size_bytes"))
            if sent is not None or recv is not None:
                log_total = (sent or 0) + (recv or 0)
                break
            if size is not None:
                log_total = size
                break

        return conn_total if conn_total is not None else log_total

    @staticmethod
    def _extract_elapsed_seconds(connection: dict[str, Any], logs: list[dict[str, Any]]) -> int:
        def to_epoch_ms(value: Any) -> int | None:
            number = _to_int(value)
            if number is None or number <= 0:
                return None
            if number < 10_000_000_000:
                return number * 1000
            return number

        starts: list[int] = []
        ends: list[int] = []

        for key in ("connection_time", "start_time"):
            v = to_epoch_ms(connection.get(key))
            if v is not None:
                starts.append(v)

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            for transfer in transfers:
                if not isinstance(transfer, dict):
                    continue
                v = to_epoch_ms(transfer.get("start_time"))
                if v is not None:
                    starts.append(v)

        for key in ("current_time", "last_activity", "updated_at"):
            v = to_epoch_ms(connection.get(key))
            if v is not None:
                ends.append(v)

        for log in logs:
            for key in ("current_time", "last_activity", "timestamp", "time"):
                v = to_epoch_ms(log.get(key))
                if v is not None:
                    ends.append(v)

        if not starts:
            return 0

        end_ms = max(ends) if ends else int(datetime.now(UTC).timestamp() * 1000)
        start_ms = min(starts)
        if end_ms <= start_ms:
            return 0

        return int((end_ms - start_ms) / 1000)
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
                # SFTPGo API v2 uses "virtual_path"; also accept "path"/"file_path" for compat
                candidate = (
                    transfer.get("virtual_path")
                    or transfer.get("path")
                    or transfer.get("file_path")
                )
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
    def _looks_like_download(
        self,
        connection: dict[str, Any],
        logs: list[dict[str, Any]],
        all_download_logs: list[dict[str, Any]] | None = None,
        username: str = "",
        file_path: str = "",
    ) -> bool:
        total_bytes = self._extract_total_bytes(connection, logs) or 0

        has_download_signal = False
        if any(self._is_download_log(log) for log in logs):
            has_download_signal = True

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            for transfer in transfers:
                if not isinstance(transfer, dict):
                    continue
                op = str(transfer.get("operation_type") or "").lower()
                transfer_type = transfer.get("type")
                if op == "download" or transfer_type == 1:  # SFTPGo API v2: type 1 = download
                    has_download_signal = True
                    break

        info = str(connection.get("info") or "").lower()
        if "dl:" in info or "download" in info:
            has_download_signal = True

        if not has_download_signal:
            return False

        # A single completed segment ≥ 50 MB is unambiguous playback regardless of connection age.
        max_segment_bytes = max(
            (_to_int(log.get("size_bytes")) or 0) for log in logs
        ) if logs else 0
        if max_segment_bytes >= _MIN_SEGMENT_BYTES_FOR_PLAYBACK:
            return True

        # Active connection that has already sent ≥ 50 MB is also real.
        # 50 MB matches _MIN_SEGMENT_BYTES_FOR_PLAYBACK so browse pre-buffers
        # (Infuse scans ~10-26 MB per file) are excluded from both paths.
        if total_bytes >= _MIN_MEANINGFUL_TRANSFER_BYTES:
            return True

        # NAT-timeout reconnection pattern: the user's router drops idle TCP connections
        # every ~120 s (common default), so Infuse reconnects repeatedly.  Each individual
        # FTP segment is small (< 50 MB) but the cumulative total across all reconnects
        # within the last 30 minutes confirms real playback.
        if all_download_logs and username and file_path:
            cumulative = self._sum_log_bytes_for_file(username, file_path, all_download_logs)
            if cumulative >= _MIN_MEANINGFUL_TRANSFER_BYTES:
                logger.debug(
                    "SFTPGo NAT-reconnect detected for %s / %s — cumulative %.1f MB across segments",
                    username,
                    file_path,
                    cumulative / 1_000_000,
                )
                return True

        return False

    # ------------------------------------------------------------------
    # Log-only session creation (offline parallel downloads)
    # ------------------------------------------------------------------

    def _import_completed_log_sessions(
        self,
        download_logs: list[dict[str, Any]],
    ) -> int:
        """Create ENDED history entries for downloads that completed entirely
        between two consecutive polls — no active connection was ever seen.

        Typical scenario: a user (e.g. Antonio) uses Infuse to download content
        offline during the night.  Multiple parallel FTP connections each transfer
        at full network speed and finish in seconds.  StreamFuse never sees an
        active connection, so the normal detection path misses them.

        Groups completed Download log entries by (username, file_path) within the
        30-minute aggregation window.  When the cumulative size_bytes ≥ 50 MB and
        the group either has ≥ 5 completed segments or ≥ 60 s of cumulative
        transfer time (to exclude brief Infuse probe bursts), a new ENDED session
        is written directly to history.
        """
        now = datetime.now(UTC)
        cutoff_ts = now.timestamp() - _RECONNECT_AGGREGATE_WINDOW_SECONDS

        # Build groups: (username_lower, ftp_path_lower) → [log entries]
        raw_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for log in download_logs:
            username = str(log.get("username") or "").strip()
            ftp_path = str(log.get("file_path") or log.get("path") or "").strip()
            if not username or not ftp_path:
                continue
            if not self._looks_like_media_file(ftp_path):
                continue

            ts_raw = log.get("ts") or log.get("timestamp") or log.get("time")
            if ts_raw is not None:
                try:
                    ts = float(ts_raw)
                    if ts > 1e10:
                        ts /= 1000.0
                    if ts < cutoff_ts:
                        continue
                except (TypeError, ValueError):
                    pass

            raw_groups[(username.lower(), ftp_path.lower())].append(log)

        created = 0

        for (norm_user, _), logs in raw_groups.items():
            # --- byte threshold -----------------------------------------
            total_bytes = sum(_to_int(log.get("size_bytes")) or 0 for log in logs)
            if total_bytes < _MIN_MEANINGFUL_TRANSFER_BYTES:
                continue

            # --- probe filter -------------------------------------------
            # Real downloads/streams either produce many RETR operations or
            # take a long time.  Infuse probes generate 2-5 quick segments.
            total_elapsed_ms = sum(_to_int(log.get("elapsed_ms")) or 0 for log in logs)
            if len(logs) < _LOG_ONLY_MIN_SEGMENTS and total_elapsed_ms < _LOG_ONLY_MIN_ELAPSED_MS:
                continue

            # --- resolve original-case values ----------------------------
            username = str(logs[0].get("username") or "").strip()
            ftp_path = str(logs[0].get("file_path") or logs[0].get("path") or "").strip()

            local_path = self._normalize_media_path_for_local_fs(ftp_path)
            if not local_path or not self._looks_like_media_file(local_path):
                continue

            # --- skip if an active session already tracks this -----------
            norm_local = local_path.strip().lower()
            has_active = any(
                k.startswith(f"{norm_user}|") and k.endswith(f"|{norm_local}")
                for k in self._active_session_ids_by_key
            )
            if has_active:
                continue

            # --- skip if a recent ENDED session already exists -----------
            existing = self.session_service.repository.find_recent_ended_by_user_and_file(
                source=StreamSource.SFTPGO,
                user_name=username,
                file_path=local_path,
                within_seconds=_RECONNECT_AGGREGATE_WINDOW_SECONDS,
            )
            if existing:
                continue

            # --- derive timestamps from log entries ----------------------
            ts_values: list[float] = []
            for log in logs:
                ts_raw = log.get("ts") or log.get("timestamp") or log.get("time")
                if ts_raw is not None:
                    try:
                        ts = float(ts_raw)
                        if ts > 1e10:
                            ts /= 1000.0
                        ts_values.append(ts)
                    except (TypeError, ValueError):
                        pass

            if ts_values:
                started_at_dt = datetime.fromtimestamp(min(ts_values), tz=UTC)
                ended_at_dt = datetime.fromtimestamp(max(ts_values), tz=UTC)
            else:
                started_at_dt = now
                ended_at_dt = now

            # --- estimate bandwidth -------------------------------------
            # For parallel downloads, use wall-clock duration; fall back to
            # cumulative elapsed (which overstates parallel time) as last resort.
            wall_seconds = (ended_at_dt - started_at_dt).total_seconds()
            bandwidth_bps: int | None = None
            if wall_seconds >= 1:
                bandwidth_bps = int(total_bytes * 8 / wall_seconds)
            elif total_elapsed_ms >= 1000:
                bandwidth_bps = int(total_bytes * 8 / (total_elapsed_ms / 1000))

            # --- extract IP from logs ------------------------------------
            ip_raw = str(
                _best_log_field(logs, "ip_address")
                or _best_log_field(logs, "remote_addr")
                or _best_log_field(logs, "remote_address")
                or ""
            )
            normalized_ip = self._normalize_ip(ip_raw)

            # --- build connection dict (used by mapper) ------------------
            connection: dict[str, Any] = {
                "username": username,
                "ip_address": normalized_ip,
                "file_path": local_path,
                "bytes_sent": total_bytes,
                "start_time": int(started_at_dt.timestamp()),
            }

            # Deterministic ID: same user+file+day never creates duplicates
            day_str = started_at_dt.strftime("%Y%m%d")
            slug = abs(hash(f"{norm_user}|{norm_local}|{day_str}"))
            source_session_id = f"sftpgo-log-{slug}"

            try:
                media_info = parse_mediainfo_for_media(local_path)
                if bandwidth_bps is None and media_info:
                    bandwidth_bps = media_info.overall_bitrate_bps or media_info.video_bitrate_bps
                poster = self.poster_resolver.resolve(local_path, None)

                payload = build_sftpgo_session_payload(
                    source_session_id=source_session_id,
                    connection=connection,
                    related_logs=logs,
                    status=SessionStatus.ENDED,
                    bandwidth_bps=bandwidth_bps,
                    poster_path=str(poster),
                    media_info=media_info,
                    ended_at=ended_at_dt,
                )
                self.session_service.create_session(payload)
                logger.debug(
                    "SFTPGo log-only session created: %s / %s — %.1f MB, %d segments",
                    username,
                    local_path,
                    total_bytes / 1_000_000,
                    len(logs),
                )
                created += 1
            except Exception:
                logger.exception(
                    "Failed to create log-only SFTPGo session for %s / %s",
                    username,
                    local_path,
                )

        return created

    def _sum_log_bytes_for_file(
        self,
        username: str,
        file_path: str,
        all_logs: list[dict[str, Any]],
        window_seconds: int = _RECONNECT_AGGREGATE_WINDOW_SECONDS,
    ) -> int:
        """Sum *size_bytes* from completed Download log entries matching *username* +
        *file_path* within the last *window_seconds*.

        Used to detect NAT-timeout reconnection patterns where individual FTP
        segments are each below *_MIN_MEANINGFUL_TRANSFER_BYTES* but the
        cumulative total confirms real playback (e.g. a full movie or episode
        streamed over a connection that resets every 2 minutes).
        """
        cutoff_ts = datetime.now(UTC).timestamp() - window_seconds
        norm_user = username.strip().lower()
        norm_path = file_path.strip().lower()
        total = 0

        for log in all_logs:
            if str(log.get("username") or "").strip().lower() != norm_user:
                continue

            log_path = str(log.get("file_path") or log.get("path") or "").strip().lower()
            if norm_path and log_path and log_path != norm_path:
                continue

            # Time-window guard — skip entries older than the rolling window.
            ts_raw = log.get("ts") or log.get("timestamp") or log.get("time")
            if ts_raw is not None:
                try:
                    ts = float(ts_raw)
                    if ts > 1e10:        # milliseconds → seconds
                        ts /= 1000.0
                    if ts < cutoff_ts:
                        continue
                except (TypeError, ValueError):
                    pass  # unparseable timestamp → include (safe default)

            total += _to_int(log.get("size_bytes")) or 0

        return total

    def _is_download_connection(self, connection: dict[str, Any]) -> bool:
        has_download_signal = False

        transfers = connection.get("active_transfers")
        if isinstance(transfers, list):
            if any(
                isinstance(transfer, dict)
                and (
                    str(transfer.get("operation_type") or "").lower() == "download"
                    or transfer.get("type") == 1  # SFTPGo API v2: type 1 = download
                )
                for transfer in transfers
            ):
                has_download_signal = True

        info = str(connection.get("info") or "").lower()
        if "dl:" in info or "download" in info:
            has_download_signal = True

        file_path = connection.get("file_path") or connection.get("path") or connection.get("current_path")
        bytes_sent = _to_int(connection.get("bytes_sent")) or 0

        # ≥ 50 MB already sent with a media path is a strong signal on its own.
        # No duration gate: FTP clients like Infuse reconnect frequently, resetting
        # connection_time each time, so a fixed elapsed threshold would never be met.
        # 50 MB threshold also keeps Infuse library-scan pre-buffers (10-26 MB) out.
        if file_path and bytes_sent >= _MIN_MEANINGFUL_TRANSFER_BYTES:
            has_download_signal = True

        return has_download_signal
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

        # bytes_sent/bytes_received are cumulative counters from the SFTPGo API —
        # each connection reports how many bytes it has transferred so far.
        # Multiple connections for the same logical session are parallel TCP reconnects
        # (e.g. Infuse re-connecting), so we take the MAX not the SUM.
        merged["bytes_sent"] = max(
            _to_int(current.get("bytes_sent")) or 0,
            _to_int(incoming.get("bytes_sent")) or 0,
        )
        merged["bytes_received"] = max(
            _to_int(current.get("bytes_received")) or 0,
            _to_int(incoming.get("bytes_received")) or 0,
        )
        return merged

    @staticmethod
    def _is_download_log(log: dict[str, Any]) -> bool:
        # SFTPGo standard log format: transfer events use sender="Download"
        sender = str(log.get("sender") or "").lower()
        if sender == "download":
            return True

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







