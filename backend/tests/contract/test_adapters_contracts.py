from app.adapters.sftpgo.contracts import SFTPGoRawTransfer
from app.adapters.tautulli.contracts import TautulliRawSession


def test_tautulli_contract_keys() -> None:
    sample: TautulliRawSession = {"session_id": "1", "user": "alice"}
    assert sample["session_id"] == "1"


def test_sftpgo_contract_keys() -> None:
    sample: SFTPGoRawTransfer = {"connection_id": "c1", "username": "bob"}
    assert sample["connection_id"] == "c1"
