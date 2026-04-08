from dataclasses import dataclass


@dataclass(slots=True)
class SyncCursor:
    source: str
    value: str
