from enum import Enum


class StreamSource(str, Enum):
    TAUTULLI = "tautulli"
    SFTPGO = "sftpgo"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


class MediaType(str, Enum):
    MOVIE = "movie"
    EPISODE = "episode"
    LIVE = "live"
    FILE_TRANSFER = "file_transfer"
    OTHER = "other"
