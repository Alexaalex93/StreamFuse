from __future__ import annotations

from datetime import datetime, timezone

from app.api.v1.schemas.dashboard import (
    DashboardWidgetResponse,
    DashboardWidgetSession,
    DashboardWidgetSummary,
)
from app.domain.enums import StreamSource
from app.persistence.repositories.unified_stream_session_repository import (
    SessionQueryFilters,
    UnifiedStreamSessionRepository,
)


class DashboardWidgetService:
    def __init__(self, repository: UnifiedStreamSessionRepository) -> None:
        self.repository = repository

    def get_widget_payload(self, limit: int = 5) -> DashboardWidgetResponse:
        active_rows = self.repository.list_active(SessionQueryFilters(limit=1000))

        visible_rows = active_rows[:limit]
        hidden_count = max(0, len(active_rows) - len(visible_rows))

        tautulli_count = sum(1 for row in active_rows if row.source == StreamSource.TAUTULLI)
        sftpgo_count = sum(1 for row in active_rows if row.source == StreamSource.SFTPGO)
        total_bandwidth_bps = sum(row.bandwidth_bps or 0 for row in active_rows)

        sessions = [
            DashboardWidgetSession(
                id=row.id,
                title=row.title or row.file_name or "Untitled",
                user_name=row.user_name,
                source=row.source,
                media_type=row.media_type,
                bandwidth_bps=row.bandwidth_bps,
                bandwidth_human=row.bandwidth_human,
                ip_address=row.ip_address,
                poster_url=f"/api/v1/posters/{row.id}",
            )
            for row in visible_rows
        ]

        summary = DashboardWidgetSummary(
            active_sessions=len(active_rows),
            tautulli_sessions=tautulli_count,
            sftpgo_sessions=sftpgo_count,
            total_bandwidth_bps=total_bandwidth_bps,
            total_bandwidth_human=_format_bps(total_bandwidth_bps),
            updated_at=datetime.now(timezone.utc),
        )

        return DashboardWidgetResponse(
            summary=summary,
            sessions=sessions,
            hidden_count=hidden_count,
        )


def _format_bps(bps: int) -> str:
    if bps <= 0:
        return "0 Mbps"
    mbps = bps / 1_000_000
    if mbps < 1000:
        return f"{mbps:.1f} Mbps"
    return f"{(mbps / 1000):.2f} Gbps"