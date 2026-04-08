from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate, UnifiedStreamSessionResponse
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions")


@router.get("", response_model=list[UnifiedStreamSessionResponse])
def list_sessions(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[UnifiedStreamSessionResponse]:
    service = SessionService(UnifiedStreamSessionRepository(db))
    rows = service.list_active_sessions(limit=limit)
    return [UnifiedStreamSessionResponse.model_validate(row) for row in rows]


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
    rows = service.insert_mock_sessions()
    return [UnifiedStreamSessionResponse.model_validate(row) for row in rows]
