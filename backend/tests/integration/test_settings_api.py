from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.main import app
from app.persistence.db import Base
from app.persistence.models import app_setting  # noqa: F401


def _auth_headers(client: TestClient) -> dict[str, str]:
    auth = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Alex1234"},
    )
    assert auth.status_code == 200
    token = auth.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_settings_defaults_and_update_roundtrip() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        headers = _auth_headers(client)

        initial = client.get("/api/v1/settings", headers=headers)
        assert initial.status_code == 200
        initial_json = initial.json()
        assert initial_json["polling_frequency_seconds"] >= 5
        assert initial_json["tautulli_api_key_set"] is False
        assert initial_json["sftpgo_token_set"] is False

        payload = {
            "tautulli_url": "http://tautulli.local:8181",
            "tautulli_api_key": "tautulli-secret-123",
            "sftpgo_url": "http://sftpgo.local:8080",
            "sftpgo_token": "sftpgo-secret-abc",
            "sftpgo_logs_path": "/srv/sftpgo/logs/transfers.json",
            "polling_frequency_seconds": 20,
            "timezone": "Europe/Madrid",
            "media_root_paths": ["/media/movies", "/media/series"],
            "preferred_poster_names": ["poster.jpg", "folder.jpg"],
            "user_aliases": {"alex_aalex93": "Alex", "sil.g8": "Sil"},
            "placeholder_path": "app/poster_resolver/assets/placeholder.svg",
            "history_retention_days": 45,
        }
        updated = client.put("/api/v1/settings", json=payload, headers=headers)
        assert updated.status_code == 200

        updated_json = updated.json()
        assert updated_json["tautulli_url"] == payload["tautulli_url"]
        assert updated_json["sftpgo_url"] == payload["sftpgo_url"]
        assert updated_json["polling_frequency_seconds"] == payload["polling_frequency_seconds"]
        assert updated_json["timezone"] == payload["timezone"]
        assert updated_json["history_retention_days"] == payload["history_retention_days"]
        assert updated_json["media_root_paths"] == payload["media_root_paths"]
        assert updated_json["preferred_poster_names"] == payload["preferred_poster_names"]
        assert updated_json["user_aliases"] == payload["user_aliases"]
        assert updated_json["tautulli_api_key_set"] is True
        assert updated_json["sftpgo_token_set"] is True
        assert payload["tautulli_api_key"] not in (updated_json["tautulli_api_key_masked"] or "")
        assert payload["sftpgo_token"] not in (updated_json["sftpgo_token_masked"] or "")

        fetched_again = client.get("/api/v1/settings", headers=headers)
        assert fetched_again.status_code == 200
        refetched_json = fetched_again.json()
        assert refetched_json["tautulli_url"] == payload["tautulli_url"]
        assert refetched_json["sftpgo_logs_path"] == payload["sftpgo_logs_path"]
        assert refetched_json["user_aliases"]["alex_aalex93"] == "Alex"
    finally:
        app.dependency_overrides.clear()


def test_settings_reject_invalid_values() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        headers = _auth_headers(client)
        response = client.put(
            "/api/v1/settings",
            json={
                "tautulli_url": "tautulli.local",
                "polling_frequency_seconds": 1,
                "timezone": "Invalid/Timezone",
                "history_retention_days": 0,
            },
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
