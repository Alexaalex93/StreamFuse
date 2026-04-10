from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.stats import (
    OverviewStatsResponse,
    TopMediaResponse,
    TopUsersResponse,
    UserInsightsResponse,
)
from app.services.stats_service import StatsFilters, StatsService

router = APIRouter(prefix="/stats")


@router.get("", response_model=OverviewStatsResponse)
def get_stats_default(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> OverviewStatsResponse:
    service = StatsService(db)
    data = service.get_overview(StatsFilters(date_from=date_from, date_to=date_to))
    return OverviewStatsResponse(**data)


@router.get("/overview", response_model=OverviewStatsResponse)
def get_overview_stats(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> OverviewStatsResponse:
    service = StatsService(db)
    data = service.get_overview(StatsFilters(date_from=date_from, date_to=date_to))
    return OverviewStatsResponse(**data)


@router.get("/users", response_model=TopUsersResponse)
def get_top_users(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TopUsersResponse:
    service = StatsService(db)
    items = service.get_top_users(StatsFilters(date_from=date_from, date_to=date_to), limit=limit)
    return TopUsersResponse(items=items)


@router.get("/media", response_model=TopMediaResponse)
def get_top_media(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TopMediaResponse:
    service = StatsService(db)
    data = service.get_top_media(StatsFilters(date_from=date_from, date_to=date_to), limit=limit)
    return TopMediaResponse(**data)


@router.get("/users/insights", response_model=UserInsightsResponse)
def get_user_insights(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> UserInsightsResponse:
    service = StatsService(db)
    data = service.get_user_insights(StatsFilters(date_from=date_from, date_to=date_to), limit=limit)
    return UserInsightsResponse(**data)
