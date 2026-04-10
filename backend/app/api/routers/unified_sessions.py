from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionResponse
from app.domain.enums import MediaType, StreamSource
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.unified_session_service import UnifiedSessionService
from app.services.user_alias_service import UserAliasService

router = APIRouter()


def _with_aliases(rows: list, alias_service: UserAliasService) -> list[UnifiedStreamSessionResponse]:
    items: list[UnifiedStreamSessionResponse] = []
    for row in rows:
        item = UnifiedStreamSessionResponse.model_validate(row)
        item.user_name = alias_service.resolve(item.user_name)
        items.append(item)
    return items


@router.get("/active", response_model=list[UnifiedStreamSessionResponse])
def get_active_sessions(
    user_name: str | None = Query(default=None),
    source: StreamSource | None = Query(default=None),
    media_type: MediaType | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[UnifiedStreamSessionResponse]:
    service = UnifiedSessionService(UnifiedStreamSessionRepository(db))
    alias_service = UserAliasService(db)
    rows = service.get_active_sessions(
        user_name=user_name,
        source=source,
        media_type=media_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return _with_aliases(rows, alias_service)


@router.get("/history", response_model=list[UnifiedStreamSessionResponse])
def get_history(
    user_name: str | None = Query(default=None),
    source: StreamSource | None = Query(default=None),
    media_type: MediaType | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[UnifiedStreamSessionResponse]:
    service = UnifiedSessionService(UnifiedStreamSessionRepository(db))
    alias_service = UserAliasService(db)
    rows = service.get_history(
        user_name=user_name,
        source=source,
        media_type=media_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return _with_aliases(rows, alias_service)
