from sqlalchemy.orm import Session

from app.domain.entities.events import ActivityEvent
from app.persistence.models.activity_event import ActivityEventModel


class SQLAlchemyActivityEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_many(self, events: list[ActivityEvent]) -> None:
        rows = [
            ActivityEventModel(
                event_id=event.event_id,
                source_system=event.source.value,
                event_type=event.event_type,
                timestamp=event.timestamp,
            )
            for event in events
        ]
        self.session.add_all(rows)
        self.session.commit()
