from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.sftpgo.client import SFTPGoClient
from app.adapters.sftpgo.mapper import build_sftpgo_session_payload
from app.domain.enums import SessionStatus, StreamSource
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
from app.poster_resolver.resolver import PosterResolver
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class SFTPGoSyncService:
    def __init__(
        self,
        client: SFTPGoClient,
        session_service: SessionService,
        poster_resolver: PosterResolver,
        stale_seconds: int = 180,
    ) -> None:
        self.client = client
        self.session_service = session_service
        self.poster_resolver = poster_resolver
        self.stale_seconds = stale_seconds
        self._last_sample: dict[str, tuple[int, datetime]] = {}

    async def poll_once(self, log_limit: int = 200) -> dict[str, int]:
        active_connections = await self.client.fetch_active_connections()
        logs = await self.client.fetch_transfer_logs(limit=log_limit)

        log_index = self._index_logs(logs)
        seen_ids: set[str] = set()
        imported = 0
        errors = 0

        for connection in active_connections:
            try:
                source_session_id = self._resolve_session_id(connection)
                if not source_session_id:
                    errors += 1
                    continue

                seen_ids.add(source_session_id)
                related_logs = self._correlate_logs(connection, log_index)
                bandwidth_bps = self._estimate_bandwidth_bps(source_session_id, connection, related_logs)

                media_path = self._resolve_file_path(connection, related_logs)
                media_info = parse_mediainfo_for_media(media_path)
                poster = self.poster_resolver.resolve(media_path, None) if media_path else self.poster_resolver.placeholder

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

    def _mark_stale_sessions(self, active_ids: set[str]) -> int:
        now = datetime.now(timezone.utc)
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
        ip_addr = str(connection.get("ip_address") or connection.get("remote_address") or "")
        path = str(connection.get("file_path") or connection.get("path") or connection.get("current_path") or "")

        correlated: list[dict[str, Any]] = []
        for logs in log_index.values():
            for log in logs:
                if username and str(log.get("username") or "") != username:
                    continue
                if ip_addr and str(log.get("ip_address") or "") and str(log.get("ip_address")) != ip_addr:
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
        now = datetime.now(timezone.utc)
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
    def _resolve_session_id(connection: dict[str, Any]) -> str:
        raw = connection.get("connection_id") or connection.get("id")
        if raw:
            return str(raw)

        user = str(connection.get("username") or "unknown")
        ip_addr = str(connection.get("ip_address") or connection.get("remote_address") or "unknown")
        path = str(connection.get("file_path") or connection.get("path") or connection.get("current_path") or "")
        return f"sftpgo-{user}-{ip_addr}-{path}".strip("-")

    @staticmethod
    def _resolve_file_path(connection: dict[str, Any], logs: list[dict[str, Any]]) -> str | None:
        path = connection.get("file_path") or connection.get("path") or connection.get("current_path")
        if path:
            return str(path)

        for log in reversed(logs):
            value = log.get("file_path") or log.get("path")
            if value:
                return str(value)
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
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)