from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.api.v1.schemas.settings import StreamFuseSettingsResponse, StreamFuseSettingsUpdate
from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.services.settings_service import SettingsService

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