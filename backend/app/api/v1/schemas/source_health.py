from datetime import datetime

from pydantic import BaseModel


class SourceHealthItem(BaseModel):
    configured: bool
    connected: bool
    status: str
    reason: str | None = None


class SourceHealthResponse(BaseModel):
    tautulli: SourceHealthItem
    sftpgo: SourceHealthItem
    samba: SourceHealthItem
    updated_at: datetime
