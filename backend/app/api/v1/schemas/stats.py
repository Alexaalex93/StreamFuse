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


class LabeledSessionsPoint(BaseModel):
    label: str
    sessions: int


class HourSessionsPoint(BaseModel):
    hour: int
    sessions: int


class DailySharedPoint(BaseModel):
    day: str
    shared_bytes: int


class HourSharedPoint(BaseModel):
    hour: int
    shared_bytes: int


class OverviewStatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    ended_sessions: int
    stale_sessions: int
    total_shared_bytes: int
    total_shared_human: str
    sessions_by_day: list[DailySessionsPoint]
    sessions_by_week: list[DailySessionsPoint]
    sessions_by_month: list[DailySessionsPoint]
    sessions_by_year: list[DailySessionsPoint]
    bandwidth_by_day: list[DailyBandwidthPoint]
    bandwidth_by_week: list[DailyBandwidthPoint]
    bandwidth_by_month: list[DailyBandwidthPoint]
    bandwidth_by_year: list[DailyBandwidthPoint]
    source_distribution: list[SourceCount]
    active_by_source: list[SourceCount]
    play_count_by_weekday: list[LabeledSessionsPoint]
    play_count_by_hour: list[HourSessionsPoint]
    play_count_by_platform: list[LabeledSessionsPoint]
    play_count_by_media_type: list[LabeledSessionsPoint]
    shared_by_day: list[DailySharedPoint]
    shared_by_week: list[DailySharedPoint]
    shared_by_month: list[DailySharedPoint]
    shared_by_year: list[DailySharedPoint]
    shared_by_hour: list[HourSharedPoint]


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
    sample_session_id: int | None


class TopMediaResponse(BaseModel):
    top_movies: list[TopMediaItem]
    top_series: list[TopMediaItem]


class UserInsightsItem(BaseModel):
    user_name: str
    total_sessions: int
    movie_sessions: int
    episode_sessions: int
    total_watch_hours: float
    movie_watch_hours: float
    episode_watch_hours: float
    unique_titles_monthly: int
    unique_movies_monthly: int
    unique_series_monthly: int
    last_seen_at: datetime | None


class UserInsightsLeader(BaseModel):
    user_name: str
    value: float


class UserInsightsLeaders(BaseModel):
    most_sessions_user: UserInsightsLeader
    most_watch_hours_user: UserInsightsLeader
    most_movies_user: UserInsightsLeader
    most_series_user: UserInsightsLeader


class PeakHourPoint(BaseModel):
    hour: int
    sessions: int


class UserInsightsResponse(BaseModel):
    items: list[UserInsightsItem]
    leaders: UserInsightsLeaders
    peak_hours: list[PeakHourPoint]
    timezone: str
    play_count_rule: str
