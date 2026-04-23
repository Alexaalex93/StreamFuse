from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.adapters.sftpgo.contracts import SFTPGoRawConnection, SFTPGoRawTransferLog
from app.adapters.sftpgo.log_parser import parse_transfer_log_file


class SFTPGoProvider:
    async def fetch_active_connections(self) -> list[SFTPGoRawConnection]:
        raise NotImplementedError

    async def fetch_transfer_logs(self, limit: int = 200) -> list[SFTPGoRawTransferLog]:
        raise NotImplementedError


@dataclass(slots=True)
class SFTPGoHTTPProvider(SFTPGoProvider):
    base_url: str
    api_key: str
    transfer_log_json_path: str | None = None
    timeout_seconds: float = 15.0

    async def fetch_active_connections(self) -> list[SFTPGoRawConnection]:
        headers = {
            "X-SFTPGO-API-KEY": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url.rstrip('/')}/api/v2/connections", headers=headers)
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            items = payload.get("items") or payload.get("connections") or []
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    async def fetch_transfer_logs(self, limit: int = 200) -> list[SFTPGoRawTransferLog]:
        rows = parse_transfer_log_file(self.transfer_log_json_path, limit=limit)
        return [item for item in rows if isinstance(item, dict)]


@dataclass(slots=True)
class SFTPGoMockProvider(SFTPGoProvider):
    _tick: int = 0

    async def fetch_active_connections(self) -> list[SFTPGoRawConnection]:
        self._tick += 1
        # Start above the 50 MB threshold so _looks_like_download considers this
        # a real playback session rather than a library-scan pre-buffer.
        base_sent = 60_000_000 + (self._tick * 6_000_000)
        return [
            {
                "connection_id": "mock-conn-1",
                "username": "sftp_user",
                "protocol": "sftp",
                "ip_address": "192.168.1.88",
                "start_time": 1710000000,
                "last_activity": 1710000000 + (self._tick * 10),
                "file_path": "/media/series/The Expanse/Season 2/The.Expanse.S02E05.mkv",
                "bytes_sent": base_sent,
                "bytes_received": 0,
            }
        ]

    async def fetch_transfer_logs(self, limit: int = 200) -> list[SFTPGoRawTransferLog]:
        return [
            {
                "ts": 1710000010,
                "event": "upload",
                "connection_id": "mock-conn-1",
                "username": "sftp_user",
                "ip_address": "192.168.1.88",
                "file_path": "/media/series/The Expanse/Season 2/The.Expanse.S02E05.mkv",
                "bytes_sent": 20_000_000,
            },
            {
                "ts": 1710000020,
                "event": "download",
                "connection_id": "mock-conn-1",
                "username": "sftp_user",
                "ip_address": "192.168.1.88",
                "file_path": "/media/series/The Expanse/Season 2/The.Expanse.S02E05.mkv",
                "bytes_sent": 30_000_000,
            },
        ][:limit]


class SFTPGoClient:
    def __init__(self, provider: SFTPGoProvider) -> None:
        self.provider = provider

    async def fetch_active_connections(self) -> list[SFTPGoRawConnection]:
        return await self.provider.fetch_active_connections()

    async def fetch_transfer_logs(self, limit: int = 200) -> list[SFTPGoRawTransferLog]:
        return await self.provider.fetch_transfer_logs(limit=limit)

    async def fetch_activity(self) -> list[dict]:
        return await self.fetch_active_connections()

