from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="STREAMFUSE_", extra="ignore")

    env: str = "development"
    debug: bool = True
    database_url: str = "sqlite:///./streamfuse.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    tautulli_base_url: str = "http://localhost:8181"
    tautulli_api_key: str = "changeme"
    tautulli_use_mock: bool = False
    tautulli_history_length: int = 100

    sftpgo_base_url: str = "http://localhost:8080"
    sftpgo_api_key: str = "changeme"
    sftpgo_use_mock: bool = True
    sftpgo_transfer_log_json_path: str = ""
    sftpgo_path_mappings: str = ""
    sftpgo_stale_seconds: int = 180
    sftpgo_log_limit: int = 200

    background_sync_enabled: bool = True
    background_sync_interval_seconds: int = 30

    poster_placeholder_path: str = "app/poster_resolver/assets/placeholder.svg"
    poster_allowed_roots: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
