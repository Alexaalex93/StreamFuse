from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SambaProvider:
    async def fetch_status(self) -> dict[str, Any]:
        raise NotImplementedError


class SambaFileProvider(SambaProvider):
    def __init__(self, status_json_path: str) -> None:
        self.status_json_path = Path(status_json_path)

    async def fetch_status(self) -> dict[str, Any]:
        if not self.status_json_path.exists():
            raise FileNotFoundError(f"Samba status file not found: {self.status_json_path}")

        raw = self.status_json_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            return parsed

        last_object: dict[str, Any] | None = None
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                last_object = candidate

        return last_object or {}


class SambaClient:
    def __init__(self, provider: SambaProvider) -> None:
        self.provider = provider

    async def fetch_active_connections(self) -> list[dict[str, Any]]:
        payload = await self.provider.fetch_status()
        if not isinstance(payload, dict):
            return []

        sessions = payload.get("sessions")
        open_files = payload.get("open_files")

        if isinstance(open_files, dict) and open_files:
            return self._from_open_files(sessions, open_files)

        if isinstance(sessions, dict):
            return [value for value in sessions.values() if isinstance(value, dict)]
        if isinstance(sessions, list):
            return [value for value in sessions if isinstance(value, dict)]

        return []

    def _from_open_files(self, sessions: Any, open_files: dict[str, Any]) -> list[dict[str, Any]]:
        session_records: list[dict[str, Any]] = []
        if isinstance(sessions, dict):
            session_records = [value for value in sessions.values() if isinstance(value, dict)]
        elif isinstance(sessions, list):
            session_records = [value for value in sessions if isinstance(value, dict)]

        by_pid: dict[str, dict[str, Any]] = {}
        for session in session_records:
            server = session.get("server_id") if isinstance(session.get("server_id"), dict) else {}
            pid = str(server.get("pid") or "").strip()
            if pid:
                by_pid[pid] = session

        grouped: dict[str, dict[str, Any]] = {}

        for open_path, open_entry in open_files.items():
            if not isinstance(open_entry, dict):
                continue

            path = str(open_path or "").strip()
            if not path:
                continue

            opens = open_entry.get("opens")
            if not isinstance(opens, dict):
                continue

            for open_info in opens.values():
                if not isinstance(open_info, dict):
                    continue

                server = open_info.get("server_id") if isinstance(open_info.get("server_id"), dict) else {}
                pid = str(server.get("pid") or "").strip()
                session = by_pid.get(pid, {})

                username = str(session.get("username") or open_info.get("username") or "unknown")
                remote_address = _session_remote_address(session)
                protocol = str(session.get("session_dialect") or "SMB")
                opened_at = open_info.get("opened_at")

                key = f"{username.lower()}|{remote_address}|{path.lower()}"
                row = grouped.get(key)
                transfer = {
                    "operation_type": "download",
                    "path": path,
                    "start_time": opened_at,
                    "size": None,
                }

                if row is None:
                    grouped[key] = {
                        "username": username,
                        "remote_address": remote_address,
                        "connection_time": session.get("creation_time") or opened_at,
                        "protocol": protocol,
                        "active_transfers": [transfer],
                        "command": "READ",
                    }
                else:
                    transfers = row.get("active_transfers")
                    if isinstance(transfers, list):
                        transfers.append(transfer)

        return list(grouped.values())


def _session_remote_address(session: dict[str, Any]) -> str:
    remote_machine = str(session.get("remote_machine") or "").strip()
    if remote_machine:
        return remote_machine

    hostname = str(session.get("hostname") or "").strip()
    if hostname:
        # example: ipv4:192.168.0.149:58082
        parts = hostname.split(":")
        if len(parts) >= 2:
            return parts[1]

    channels = session.get("channels") if isinstance(session.get("channels"), dict) else {}
    for channel in channels.values():
        if not isinstance(channel, dict):
            continue
        remote = str(channel.get("remote_address") or "").strip()
        if not remote:
            continue
        # example: ipv4:192.168.0.149:58082
        parts = remote.split(":")
        if len(parts) >= 2:
            return parts[1]

    return ""
