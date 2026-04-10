from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate, UnifiedStreamSessionResponse
from app.domain.enums import StreamSource
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.session_service import SessionService
from app.services.user_alias_service import UserAliasService

router = APIRouter(prefix="/sessions")


@router.get("", response_model=list[UnifiedStreamSessionResponse])
def list_sessions(
    limit: int = Query(default=100, ge=1, le=500),
    source: StreamSource | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[UnifiedStreamSessionResponse]:
    service = SessionService(UnifiedStreamSessionRepository(db))
    alias_service = UserAliasService(db)
    rows = service.list_active_sessions(limit=limit, source=source)

    items: list[UnifiedStreamSessionResponse] = []
    for row in rows:
        item = UnifiedStreamSessionResponse.model_validate(row)
        item.user_name = alias_service.resolve(item.user_name)
        items.append(item)
    return items


@router.post("", response_model=UnifiedStreamSessionResponse)
def create_session(
    payload: UnifiedStreamSessionCreate,
    db: Session = Depends(get_db),
) -> UnifiedStreamSessionResponse:
    service = SessionService(UnifiedStreamSessionRepository(db))
    row = service.create_session(payload)
    return UnifiedStreamSessionResponse.model_validate(row)


@router.post("/mock", response_model=list[UnifiedStreamSessionResponse])
def create_mock_sessions(db: Session = Depends(get_db)) -> list[UnifiedStreamSessionResponse]:
    service = SessionService(UnifiedStreamSessionRepository(db))
    alias_service = UserAliasService(db)
    rows = service.insert_mock_sessions()

    items: list[UnifiedStreamSessionResponse] = []
    for row in rows:
        item = UnifiedStreamSessionResponse.model_validate(row)
        item.user_name = alias_service.resolve(item.user_name)
        items.append(item)
    return items
