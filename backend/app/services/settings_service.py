import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.api.v1.schemas.settings import StreamFuseSettingsResponse, StreamFuseSettingsUpdate
from app.core.config import Settings
from app.persistence.models.app_setting import AppSettingModel
from app.persistence.repositories.app_setting_repository import AppSettingRepository

DEFAULT_PREFERRED_POSTER_NAMES = ["poster.jpg", "cover.jpg", "folder.jpg", "movie.jpg", "series.jpg"]


class SettingsService:
    KEY_TAUTULLI_URL = "tautulli_url"
    KEY_TAUTULLI_API_KEY = "tautulli_api_key"
    KEY_SFTPGO_URL = "sftpgo_url"
    KEY_SFTPGO_TOKEN = "sftpgo_token"
    KEY_SFTPGO_LOGS_PATH = "sftpgo_logs_path"
    KEY_POLLING_FREQUENCY_SECONDS = "polling_frequency_seconds"
    KEY_TIMEZONE = "timezone"
    KEY_MEDIA_ROOT_PATHS = "media_root_paths"
    KEY_PREFERRED_POSTER_NAMES = "preferred_poster_names"
    KEY_PLACEHOLDER_PATH = "placeholder_path"
    KEY_HISTORY_RETENTION_DAYS = "history_retention_days"

    SETTING_DESCRIPTIONS = {
        KEY_TAUTULLI_URL: "Tautulli base URL",
        KEY_TAUTULLI_API_KEY: "Tautulli API key (secret)",
        KEY_SFTPGO_URL: "SFTPGo base URL",
        KEY_SFTPGO_TOKEN: "SFTPGo token/API key (secret)",
        KEY_SFTPGO_LOGS_PATH: "SFTPGo transfer logs JSON path",
        KEY_POLLING_FREQUENCY_SECONDS: "Polling frequency in seconds",
        KEY_TIMEZONE: "Display timezone",
        KEY_MEDIA_ROOT_PATHS: "Media root paths as JSON list",
        KEY_PREFERRED_POSTER_NAMES: "Preferred poster file names as JSON list",
        KEY_PLACEHOLDER_PATH: "Placeholder image path",
        KEY_HISTORY_RETENTION_DAYS: "History retention in days",
    }

    def __init__(self, repository: AppSettingRepository, app_settings: Settings) -> None:
        self.repository = repository
        self.app_settings = app_settings

    @property
    def _all_setting_keys(self) -> list[str]:
        return list(self.SETTING_DESCRIPTIONS.keys())

    def get_settings(self) -> StreamFuseSettingsResponse:
        rows = self.repository.get_many(self._all_setting_keys)
        by_key = {row.key: row for row in rows}

        tautulli_secret = self._value_or_default(
            by_key,
            self.KEY_TAUTULLI_API_KEY,
            self._default_secret(self.app_settings.tautulli_api_key),
        )
        sftpgo_secret = self._value_or_default(
            by_key,
            self.KEY_SFTPGO_TOKEN,
            self._default_secret(self.app_settings.sftpgo_api_key),
        )

        response = StreamFuseSettingsResponse(
            tautulli_url=self._value_or_default(by_key, self.KEY_TAUTULLI_URL, self.app_settings.tautulli_base_url),
            tautulli_api_key_set=bool(tautulli_secret),
            tautulli_api_key_masked=self._mask_secret(tautulli_secret),
            sftpgo_url=self._value_or_default(by_key, self.KEY_SFTPGO_URL, self.app_settings.sftpgo_base_url),
            sftpgo_token_set=bool(sftpgo_secret),
            sftpgo_token_masked=self._mask_secret(sftpgo_secret),
            sftpgo_logs_path=self._value_or_default(
                by_key,
                self.KEY_SFTPGO_LOGS_PATH,
                self.app_settings.sftpgo_transfer_log_json_path,
            )
            or None,
            polling_frequency_seconds=int(
                self._value_or_default(
                    by_key,
                    self.KEY_POLLING_FREQUENCY_SECONDS,
                    "30",
                )
            ),
            timezone=self._validated_timezone(
                self._value_or_default(by_key, self.KEY_TIMEZONE, "UTC")
            ),
            media_root_paths=self._parse_list(
                self._value_or_default(
                    by_key,
                    self.KEY_MEDIA_ROOT_PATHS,
                    self._serialize_list(self._parse_csv(self.app_settings.poster_allowed_roots)),
                )
            ),
            preferred_poster_names=self._parse_list(
                self._value_or_default(
                    by_key,
                    self.KEY_PREFERRED_POSTER_NAMES,
                    self._serialize_list(DEFAULT_PREFERRED_POSTER_NAMES),
                )
            ),
            placeholder_path=self._value_or_default(
                by_key,
                self.KEY_PLACEHOLDER_PATH,
                self.app_settings.poster_placeholder_path,
            ),
            history_retention_days=int(
                self._value_or_default(by_key, self.KEY_HISTORY_RETENTION_DAYS, "30")
            ),
            updated_at=self._latest_updated_at(rows),
        )
        return response

    def update_settings(self, payload: StreamFuseSettingsUpdate) -> StreamFuseSettingsResponse:
        if payload.tautulli_url is not None:
            self._set(self.KEY_TAUTULLI_URL, payload.tautulli_url)
        if payload.sftpgo_url is not None:
            self._set(self.KEY_SFTPGO_URL, payload.sftpgo_url)
        if payload.sftpgo_logs_path is not None:
            self._set(self.KEY_SFTPGO_LOGS_PATH, payload.sftpgo_logs_path)

        if payload.polling_frequency_seconds is not None:
            self._set(self.KEY_POLLING_FREQUENCY_SECONDS, str(payload.polling_frequency_seconds))
        if payload.timezone is not None:
            self._set(self.KEY_TIMEZONE, payload.timezone)

        if payload.media_root_paths is not None:
            self._set(self.KEY_MEDIA_ROOT_PATHS, self._serialize_list(payload.media_root_paths))
        if payload.preferred_poster_names is not None:
            self._set(self.KEY_PREFERRED_POSTER_NAMES, self._serialize_list(payload.preferred_poster_names))

        if payload.placeholder_path is not None:
            self._set(self.KEY_PLACEHOLDER_PATH, payload.placeholder_path)
        if payload.history_retention_days is not None:
            self._set(self.KEY_HISTORY_RETENTION_DAYS, str(payload.history_retention_days))

        if payload.tautulli_api_key is not None:
            self._set(self.KEY_TAUTULLI_API_KEY, payload.tautulli_api_key.strip())
        if payload.sftpgo_token is not None:
            self._set(self.KEY_SFTPGO_TOKEN, payload.sftpgo_token.strip())

        return self.get_settings()

    def _set(self, key: str, value: str) -> AppSettingModel:
        return self.repository.set(key=key, value=value, description=self.SETTING_DESCRIPTIONS[key])

    @staticmethod
    def _serialize_list(items: list[str]) -> str:
        return json.dumps(items)

    @staticmethod
    def _parse_list(raw: str) -> list[str]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]

    @staticmethod
    def _parse_csv(raw: str) -> list[str]:
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @staticmethod
    def _value_or_default(by_key: dict[str, AppSettingModel], key: str, default: str) -> str:
        row = by_key.get(key)
        if row is None:
            return default
        return row.value

    @staticmethod
    def _mask_secret(secret: str) -> str | None:
        if not secret:
            return None
        if len(secret) <= 4:
            return "*" * len(secret)
        hidden = "*" * (len(secret) - 4)
        return f"{secret[:2]}{hidden}{secret[-2:]}"

    @staticmethod
    def _default_secret(value: str) -> str:
        cleaned = (value or "").strip()
        return "" if cleaned.lower() == "changeme" else cleaned

    @staticmethod
    def _latest_updated_at(rows: list[AppSettingModel]) -> datetime | None:
        timestamps = [row.updated_at for row in rows if row.updated_at is not None]
        if not timestamps:
            return None
        return max(timestamps)

    @staticmethod
    def _validated_timezone(tz_name: str) -> str:
        try:
            ZoneInfo(tz_name)
        except Exception:
            return "UTC"
        return tz_name