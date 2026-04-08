from app.adapters.sftpgo.client import SFTPGoClient
from app.adapters.tautulli.client import TautulliClient


class SyncService:
    def __init__(self, tautulli_client: TautulliClient, sftpgo_client: SFTPGoClient) -> None:
        self.tautulli_client = tautulli_client
        self.sftpgo_client = sftpgo_client

    async def run_sync(self) -> dict[str, int]:
        tautulli_active = await self.tautulli_client.fetch_active_sessions()
        tautulli_history = await self.tautulli_client.fetch_history(length=50)
        sftpgo_active = await self.sftpgo_client.fetch_active_connections()
        sftpgo_logs = await self.sftpgo_client.fetch_transfer_logs(limit=200)

        return {
            "tautulli_active": len(tautulli_active),
            "tautulli_history": len(tautulli_history),
            "sftpgo_active": len(sftpgo_active),
            "sftpgo_logs": len(sftpgo_logs),
        }
