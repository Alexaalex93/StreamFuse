from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SourceSystem(str, Enum):
    TAUTULLI = "tautulli"
    SFTPGO = "sftpgo"


@dataclass(slots=True)
class StreamSession:
    session_id: str
    username: str
    title: str
    started_at: datetime
    source: SourceSystem = SourceSystem.TAUTULLI


@dataclass(slots=True)
class TransferSession:
    session_id: str
    username: str
    path: str
    bytes_transferred: int
    started_at: datetime
    source: SourceSystem = SourceSystem.SFTPGO
