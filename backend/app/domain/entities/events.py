from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.sessions import SourceSystem


@dataclass(slots=True)
class ActivityEvent:
    event_id: str
    event_type: str
    timestamp: datetime
    source: SourceSystem
