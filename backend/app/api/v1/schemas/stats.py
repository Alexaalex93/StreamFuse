from datetime import datetime

from pydantic import BaseModel


class SourceCount(BaseModel):
    source: str
    sessions: int


class DailySessionsPoint(BaseModel):
    day: str
    sessions: int


class DailyBandwidthPoint(BaseModel):
    day: str
    avg_bandwidth_bps: float


class OverviewStatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    ended_sessions: int
    stale_sessions: int
    total_shared_bytes: int
    total_shared_human: str
    sessions_by_day: list[DailySessionsPoint]
    sessions_by_month: list[DailySessionsPoint]
    sessions_by_year: list[DailySessionsPoint]
    bandwidth_by_day: list[DailyBandwidthPoint]
    bandwidth_by_month: list[DailyBandwidthPoint]
    bandwidth_by_year: list[DailyBandwidthPoint]
    source_distribution: list[SourceCount]
    active_by_source: list[SourceCount]


class TopUserStat(BaseModel):
    user_name: str
    sessions: int
    active_sessions: int
    avg_bandwidth_bps: float | None
    last_seen_at: datetime | None


class TopUsersResponse(BaseModel):
    items: list[TopUserStat]


class TopMediaItem(BaseModel):
    title: str
    media_type: str
    sessions: int
    unique_users: int
    avg_bandwidth_bps: float | None


class TopMediaResponse(BaseModel):
    top_movies: list[TopMediaItem]
    top_series: list[TopMediaItem]
