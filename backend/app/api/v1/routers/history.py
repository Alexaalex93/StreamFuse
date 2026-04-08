from fastapi import APIRouter

from app.api.v1.schemas.history import HistoryEventResponse

router = APIRouter(prefix="/history")


@router.get("", response_model=list[HistoryEventResponse])
def list_history() -> list[HistoryEventResponse]:
    return []
