from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.schemas.sessions import UnifiedStreamSessionCreate, UnifiedStreamSessionResponse
from app.domain.enums import StreamSource
from app.parsers.mediainfo_parser import parse_mediainfo_for_media
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.session_service import SessionService
from app.services.user_alias_service import UserAliasService

router = APIRouter(prefix="/sessions")


class BulkDeleteBody(BaseModel):
    ids: list[int]


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


@router.delete("/by-user/{user_name}", response_model=dict)
def delete_sessions_by_user(
    user_name: str,
    db: Session = Depends(get_db),
) -> dict:
    """Delete all sessions (active + history) belonging to *user_name*.

    The match is case-insensitive.  Returns ``{"deleted": N}`` with the count
    of rows removed.  Raises 404 if the user has no sessions at all.
    """
    repo = UnifiedStreamSessionRepository(db)
    deleted = repo.delete_by_user(user_name)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"No sessions found for user '{user_name}'")
    return {"deleted": deleted, "user_name": user_name}


@router.delete("/bulk", response_model=dict)
def delete_sessions_bulk(
    body: BulkDeleteBody,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a specific list of sessions by primary-key ID.

    Returns ``{"deleted": N}`` with the count of rows removed.
    """
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    repo = UnifiedStreamSessionRepository(db)
    deleted = repo.delete_by_ids(body.ids)
    return {"deleted": deleted}


@router.post("/enrich-mediainfo", response_model=dict)
def enrich_missing_mediainfo(db: Session = Depends(get_db)) -> dict:
    """Re-run mediainfo/NFO parsing for sessions that are missing bandwidth,
    resolution or codec data.  Safe to call repeatedly — only fills gaps,
    never overwrites existing values.

    Fallback chain for bandwidth (first hit wins):
    1. NFO / mediainfo XML <bitrate> field.
    2. File-size ÷ duration — reads file on disk; needs NFO <runtime> or a
       previously-stored duration_ms.
    3. Samba transfer bytes ÷ session duration — uses bytes_transferred stored
       in raw_payload.transfer.size and the session's started_at / ended_at.
       Only applied when the session lasted > 10 minutes (avoids pure
       pre-buffering runs inflating the result).

    Returns ``{"updated": N, "skipped": N, "details": [...]}`` where
    *skipped* means all three strategies failed (no NFO, file inaccessible,
    and no transfer data).
    """
    from datetime import UTC, datetime

    repo = UnifiedStreamSessionRepository(db)
    rows = repo.list_missing_mediainfo()

    updated = 0
    skipped = 0
    details: list[str] = []

    for row in rows:
        media_info = parse_mediainfo_for_media(row.file_path)

        # --- Strategy 1: NFO / mediainfo XML bitrate -------------------------
        bandwidth_bps: int | None = None
        if media_info:
            bandwidth_bps = media_info.overall_bitrate_bps or media_info.video_bitrate_bps

        # --- Strategy 2: file size ÷ duration --------------------------------
        if not bandwidth_bps and row.file_path:
            file_obj = Path(row.file_path)
            duration_ms = (
                (media_info.duration_ms if media_info else None)
                or row.duration_ms
            )
            if file_obj.is_file() and duration_ms and duration_ms > 0:
                try:
                    file_size_bytes = file_obj.stat().st_size
                    if file_size_bytes > 0:
                        bandwidth_bps = int(file_size_bytes * 8 * 1000 / duration_ms)
                except OSError:
                    pass

        # --- Strategy 3: Samba bytes_transferred ÷ session duration ----------
        # Uses data already stored in raw_payload.  Only reliable when the
        # session covered a complete (or nearly-complete) watch, so we require
        # the session to have lasted at least 10 minutes.
        if not bandwidth_bps and row.started_at and row.ended_at:
            try:
                started = row.started_at
                ended = row.ended_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=UTC)
                if ended.tzinfo is None:
                    ended = ended.replace(tzinfo=UTC)
                session_duration_s = (ended - started).total_seconds()
                if session_duration_s >= 600:   # ≥ 10 minutes
                    raw = row.raw_payload if isinstance(row.raw_payload, dict) else {}
                    transfer = raw.get("transfer") if isinstance(raw.get("transfer"), dict) else {}
                    bytes_transferred = transfer.get("size")
                    if bytes_transferred and isinstance(bytes_transferred, (int, float)) and bytes_transferred > 0:
                        bandwidth_bps = int(int(bytes_transferred) * 8 / session_duration_s)
            except Exception:
                pass

        changed = False

        if bandwidth_bps and not row.bandwidth_bps:
            row.bandwidth_bps = bandwidth_bps
            row.bandwidth_human = _fmt_bps(bandwidth_bps)
            changed = True

        if media_info:
            if media_info.resolution and not row.resolution:
                row.resolution = media_info.resolution
                changed = True
            if media_info.video_codec and not row.video_codec:
                row.video_codec = media_info.video_codec
                changed = True
            if media_info.audio_codec and not row.audio_codec:
                row.audio_codec = media_info.audio_codec
                changed = True
            if media_info.duration_ms and not row.duration_ms:
                row.duration_ms = media_info.duration_ms
                changed = True
            # Keep raw_payload.media_info in sync so the frontend
            # can also read codec/bitrate from the nested object.
            raw = row.raw_payload if isinstance(row.raw_payload, dict) else {}
            if not raw.get("media_info"):
                raw = dict(raw)
                raw["media_info"] = media_info.to_dict()
                row.raw_payload = raw
                changed = True

        if changed:
            updated += 1
        else:
            skipped += 1
            if row.file_path:
                details.append(row.file_path)

    if updated:
        db.commit()

    return {"updated": updated, "skipped": skipped, "details": details[:10]}


def _fmt_bps(bps: int) -> str:
    mbps = bps / 1_000_000
    if mbps >= 1:
        return f"{mbps:.1f} Mbps"
    return f"{bps / 1000:.1f} Kbps"


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
