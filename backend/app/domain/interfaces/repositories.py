from typing import Protocol

from app.domain.entities.events import ActivityEvent


class ActivityEventRepository(Protocol):
    def save_many(self, events: list[ActivityEvent]) -> None: ...
