from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models.app_setting import AppSettingModel


class AppSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> AppSettingModel | None:
        return self.db.scalar(select(AppSettingModel).where(AppSettingModel.key == key))

    def get_many(self, keys: list[str]) -> list[AppSettingModel]:
        if not keys:
            return []
        stmt = select(AppSettingModel).where(AppSettingModel.key.in_(keys))
        return list(self.db.scalars(stmt).all())

    def set(self, key: str, value: str, description: str | None = None) -> AppSettingModel:
        current = self.get(key)
        if current:
            current.value = value
            current.description = description
            self.db.commit()
            self.db.refresh(current)
            return current

        setting = AppSettingModel(key=key, value=value, description=description)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting