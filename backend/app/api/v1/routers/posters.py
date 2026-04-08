from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_app_settings
from app.core.config import Settings
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver

router = APIRouter(prefix="/posters")


@router.get("/{session_id}")
def get_poster(
    session_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> FileResponse:
    repository = UnifiedStreamSessionRepository(db)
    session = repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    resolver = PosterResolver(settings)
    poster_path = resolver.resolve(session.file_path, session.media_type)

    if not poster_path.exists() or not poster_path.is_file():
        raise HTTPException(status_code=404, detail="Poster not found")

    return FileResponse(path=poster_path)
