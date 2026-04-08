from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models.user import UserModel


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_name(self, user_name: str) -> UserModel | None:
        return self.db.scalar(select(UserModel).where(UserModel.user_name == user_name))

    def upsert(self, user_name: str, display_name: str | None = None) -> UserModel:
        existing = self.get_by_user_name(user_name)
        if existing:
            if display_name is not None:
                existing.display_name = display_name
                self.db.commit()
                self.db.refresh(existing)
            return existing

        user = UserModel(user_name=user_name, display_name=display_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
