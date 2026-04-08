from pydantic import BaseModel


class HistoryEventResponse(BaseModel):
    event_id: str
    source_system: str
    event_type: str
    timestamp: str
