from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.dashboard import DashboardWidgetResponse
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.dashboard_widget_service import DashboardWidgetService
from app.services.user_alias_service import UserAliasService

router = APIRouter(prefix="/dashboard")


@router.get("/widget", response_model=DashboardWidgetResponse)
def get_dashboard_widget(
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
) -> DashboardWidgetResponse:
    service = DashboardWidgetService(UnifiedStreamSessionRepository(db), UserAliasService(db))
    return service.get_widget_payload(limit=limit)
