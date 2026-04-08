from sqlalchemy.orm import Session

from app.persistence.models.ingestion_log import IngestionLogModel


class IngestionLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, log: IngestionLogModel) -> IngestionLogModel:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
