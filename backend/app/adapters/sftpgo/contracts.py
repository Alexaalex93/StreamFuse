from typing import TypedDict


class SFTPGoRawConnection(TypedDict, total=False):
    connection_id: str
    id: str
    username: str
    protocol: str
    ip_address: str
    remote_address: str
    start_time: int
    connected_at: int
    last_activity: int

    path: str
    current_path: str
    file_path: str

    bytes_sent: int
    bytes_received: int


class SFTPGoRawTransferLog(TypedDict, total=False):
    ts: int
    timestamp: int
    time: str

    event: str
    action: str

    connection_id: str
    session_id: str

    username: str
    ip_address: str
    path: str
    file_path: str

    bytes_sent: int
    bytes_received: int
    bytes_total: int

    protocol: str
