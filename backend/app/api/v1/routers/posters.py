from __future__ import annotations

from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.domain.enums import StreamSource
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.poster_resolver.resolver import PosterResolver

router = APIRouter(prefix="/posters")


def _proxy_tautulli_thumb(
    settings: Settings,
    poster_path: str | None,
    *,
    width: int,
    height: int,
) -> Response | None:
    if not poster_path:
        return None

    path = poster_path.strip()
    if not path.startswith("/library/"):
        return None

    if not settings.tautulli_base_url or not settings.tautulli_api_key or settings.tautulli_api_key == "changeme":
        return None

    endpoint = f"{settings.tautulli_base_url.rstrip('/')}/api/v2"
    img_param = quote(path, safe="/")
    target = (
        f"{endpoint}?apikey={settings.tautulli_api_key}&cmd=pms_image_proxy"
        f"&img={img_param}&width={width}&height={height}&img_format=webp"
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            image_response = client.get(target)
            image_response.raise_for_status()
            content_type = image_response.headers.get("content-type", "image/webp")
            return Response(content=image_response.content, media_type=content_type)
    except Exception:
        return None


@router.get("/{session_id}")
def get_poster(
    session_id: int,
    width: int = Query(default=300, ge=80, le=2000),
    height: int = Query(default=450, ge=80, le=2000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    repository = UnifiedStreamSessionRepository(db)
    session = repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.source == StreamSource.TAUTULLI:
        proxied = _proxy_tautulli_thumb(settings, session.poster_path, width=width, height=height)
        if proxied is not None:
            return proxied

    resolver = PosterResolver(settings)
    poster_path = resolver.resolve(session.file_path, session.media_type)

    if not poster_path.exists() or not poster_path.is_file():
        raise HTTPException(status_code=404, detail="Poster not found")

    return FileResponse(path=poster_path)
