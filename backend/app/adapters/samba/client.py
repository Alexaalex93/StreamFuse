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

        # Accept a plain JSON object or a newline-separated stream of JSON snapshots.
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
        sessions = payload.get("sessions") if isinstance(payload, dict) else None

        if isinstance(sessions, dict):
            return [value for value in sessions.values() if isinstance(value, dict)]
        if isinstance(sessions, list):
            return [value for value in sessions if isinstance(value, dict)]

        return []
