from sqlalchemy.orm import Session

from app.persistence.models.app_setting import AppSettingModel
from app.services.session_service import SessionService
from app.persistence.repositories.unified_stream_session_repository import UnifiedStreamSessionRepository


def seed_dev_data(db: Session) -> None:
    service = SessionService(UnifiedStreamSessionRepository(db))
    service.insert_mock_sessions()

    timezone = db.get(AppSettingModel, "timezone")
    if timezone is None:
        db.add(AppSettingModel(key="timezone", value="UTC", description="Default timezone"))
        db.commit()
