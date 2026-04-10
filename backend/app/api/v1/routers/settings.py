from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.api.v1.schemas.settings import DetectedUserAliasOption, StreamFuseSettingsResponse, StreamFuseSettingsUpdate
from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository
from app.services.settings_service import SettingsService
from app.services.user_alias_service import UserAliasService

router = APIRouter(prefix="/settings")


@router.get("", response_model=StreamFuseSettingsResponse)
def get_streamfuse_settings(
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_app_settings),
) -> StreamFuseSettingsResponse:
    service = SettingsService(AppSettingRepository(db), app_settings)
    return service.get_settings()


@router.put("", response_model=StreamFuseSettingsResponse)
def update_streamfuse_settings(
    payload: StreamFuseSettingsUpdate,
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_app_settings),
) -> StreamFuseSettingsResponse:
    service = SettingsService(AppSettingRepository(db), app_settings)
    return service.update_settings(payload)


@router.get("/detected-users", response_model=list[DetectedUserAliasOption])
def list_detected_users(
    db: Session = Depends(get_db),
) -> list[DetectedUserAliasOption]:
    repository = UnifiedStreamSessionRepository(db)
    alias_service = UserAliasService(db)
    rows = repository.list_detected_users()

    result: list[DetectedUserAliasOption] = []
    for row in rows:
        raw_name = str(row["user_name"])
        resolved = alias_service.resolve(raw_name)
        alias = resolved if resolved != raw_name else None
        result.append(
            DetectedUserAliasOption(
                user_name=raw_name,
                alias=alias,
                session_count=int(row["session_count"]),
                sources=[str(source) for source in row["sources"]],
            )
        )

    return result
