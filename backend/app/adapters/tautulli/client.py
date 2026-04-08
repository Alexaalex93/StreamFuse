from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.adapters.tautulli.contracts import TautulliRawHistoryItem, TautulliRawSession


class TautulliProvider(Protocol):
    async def fetch_active_sessions(self) -> list[TautulliRawSession]: ...

    async def fetch_history(self, length: int = 50) -> list[TautulliRawHistoryItem]: ...


@dataclass(slots=True)
class TautulliHTTPProvider:
    base_url: str
    api_key: str
    timeout_seconds: float = 15.0

    async def fetch_active_sessions(self) -> list[TautulliRawSession]:
        payload = await self._call("get_activity")
        data = payload.get("data", {})
        sessions = data.get("sessions", []) if isinstance(data, dict) else []
        return [item for item in sessions if isinstance(item, dict)]

    async def fetch_history(self, length: int = 50) -> list[TautulliRawHistoryItem]:
        payload = await self._call("get_history", length=length)
        data = payload.get("data", {})

        if isinstance(data, dict) and isinstance(data.get("data"), list):
            rows = data.get("data", [])
        elif isinstance(data, list):
            rows = data
        else:
            rows = []

        return [item for item in rows if isinstance(item, dict)]

    async def _call(self, cmd: str, **params: object) -> dict:
        query = {
            "apikey": self.api_key,
            "cmd": cmd,
            **params,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url.rstrip('/')}/api/v2", params=query)
            response.raise_for_status()
            body = response.json()

        if not isinstance(body, dict):
            return {}
        response_obj = body.get("response", {})
        if not isinstance(response_obj, dict):
            return {}
        return response_obj


@dataclass(slots=True)
class TautulliMockProvider:
    def _mock_active(self) -> list[TautulliRawSession]:
        return [
            {
                "session_id": "mock-active-1",
                "user": "alice",
                "ip_address": "192.168.1.50",
                "title": "Dune: Part Two",
                "full_title": "Dune: Part Two",
                "media_type": "movie",
                "duration": 9960000,
                "progress_percent": 54.2,
                "bandwidth": 14500,
                "stream_bitrate": 14500,
                "stream_video_full_resolution": "4K",
                "stream_video_codec": "hevc",
                "stream_audio_codec": "eac3",
                "player": "Plex Web",
                "product": "Web",
                "platform": "Chrome",
                "started": 1710000000,
                "transcode_decision": "direct play",
                "file": "/media/movies/Dune.Part.Two.2024.mkv",
            },
            {
                "session_id": "mock-active-2",
                "user": "bob",
                "ip_address": "192.168.1.51",
                "title": "The Expanse",
                "grandparent_title": "The Expanse",
                "parent_media_index": 2,
                "media_index": 5,
                "media_type": "episode",
                "duration": 2700000,
                "progress_percent": 18.0,
                "bandwidth": 8500,
                "stream_bitrate": 8500,
                "stream_video_full_resolution": "1080p",
                "stream_video_codec": "h264",
                "stream_audio_codec": "aac",
                "player": "Android",
                "product": "Plex for Android",
                "platform": "Android",
                "started": 1710001200,
                "transcode_decision": "transcode",
                "file": "/media/series/The Expanse/Season 2/The.Expanse.S02E05.mkv",
            },
        ]

    def _mock_history(self) -> list[TautulliRawHistoryItem]:
        return [
            {
                "session_id": "mock-history-1",
                "user": "carol",
                "ip_address": "192.168.1.52",
                "title": "Arrival",
                "media_type": "movie",
                "duration": 6960000,
                "progress_percent": 100.0,
                "bandwidth": 6000,
                "stream_bitrate": 6000,
                "stream_video_full_resolution": "1080p",
                "stream_video_codec": "h264",
                "stream_audio_codec": "ac3",
                "player": "Roku",
                "product": "Plex for Roku",
                "platform": "Roku",
                "started": 1709995000,
                "stopped": 1710001960,
                "transcode_decision": "direct stream",
                "file": "/media/movies/Arrival.2016.mkv",
            }
        ]

    async def fetch_active_sessions(self) -> list[TautulliRawSession]:
        return self._mock_active()

    async def fetch_history(self, length: int = 50) -> list[TautulliRawHistoryItem]:
        return self._mock_history()[:length]


class TautulliClient:
    def __init__(self, provider: TautulliProvider) -> None:
        self.provider = provider

    async def fetch_active_sessions(self) -> list[TautulliRawSession]:
        return await self.provider.fetch_active_sessions()

    async def fetch_history(self, length: int = 50) -> list[TautulliRawHistoryItem]:
        return await self.provider.fetch_history(length=length)
