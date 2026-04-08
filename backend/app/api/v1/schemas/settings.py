from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StreamFuseSettingsResponse(BaseModel):
    tautulli_url: str
    tautulli_api_key_set: bool
    tautulli_api_key_masked: str | None

    sftpgo_url: str
    sftpgo_token_set: bool
    sftpgo_token_masked: str | None
    sftpgo_logs_path: str | None

    polling_frequency_seconds: int
    timezone: str
    media_root_paths: list[str]
    preferred_poster_names: list[str]
    placeholder_path: str
    history_retention_days: int
    updated_at: datetime | None = None


class StreamFuseSettingsUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tautulli_url: str | None = None
    tautulli_api_key: str | None = Field(default=None, description="Only send when updating secret")

    sftpgo_url: str | None = None
    sftpgo_token: str | None = Field(default=None, description="Only send when updating secret")
    sftpgo_logs_path: str | None = None

    polling_frequency_seconds: int | None = None
    timezone: str | None = None
    media_root_paths: list[str] | None = None
    preferred_poster_names: list[str] | None = None
    placeholder_path: str | None = None
    history_retention_days: int | None = None

    @field_validator("tautulli_url", "sftpgo_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError("Invalid timezone name") from exc
        return value

    @field_validator("polling_frequency_seconds")
    @classmethod
    def validate_polling(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 5:
            raise ValueError("polling_frequency_seconds must be >= 5")
        return value

    @field_validator("history_retention_days")
    @classmethod
    def validate_retention(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1:
            raise ValueError("history_retention_days must be >= 1")
        return value

    @field_validator("media_root_paths", "preferred_poster_names")
    @classmethod
    def validate_list_items(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item.strip()]
        return cleaned