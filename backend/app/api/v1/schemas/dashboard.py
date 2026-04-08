from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import MediaType, StreamSource


class DashboardWidgetSummary(BaseModel):
    active_sessions: int
    tautulli_sessions: int
    sftpgo_sessions: int
    total_bandwidth_bps: int
    total_bandwidth_human: str
    updated_at: datetime


class DashboardWidgetSession(BaseModel):
    id: int
    title: str
    user_name: str
    source: StreamSource
    media_type: MediaType
    bandwidth_bps: int | None
    bandwidth_human: str | None
    ip_address: str | None
    poster_url: str


class DashboardWidgetResponse(BaseModel):
    summary: DashboardWidgetSummary
    sessions: list[DashboardWidgetSession]
    hidden_count: int