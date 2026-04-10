from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models.app_setting import AppSettingModel


class UserAliasService:
    KEY_USER_ALIASES = "user_aliases"

    def __init__(self, db: Session) -> None:
        self.db = db
        self._aliases = self._load_aliases()
        self._aliases_lower = {key.lower(): value for key, value in self._aliases.items()}

    def resolve(self, user_name: str | None) -> str:
        raw = (user_name or "").strip()
        if not raw:
            return "unknown"
        return self._aliases.get(raw) or self._aliases_lower.get(raw.lower()) or raw

    def _load_aliases(self) -> dict[str, str]:
        row = self.db.scalar(select(AppSettingModel).where(AppSettingModel.key == self.KEY_USER_ALIASES))
        if row is None or not row.value:
            return {}
        try:
            parsed = json.loads(row.value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}

        cleaned: dict[str, str] = {}
        for source, alias in parsed.items():
            source_name = str(source).strip()
            alias_name = str(alias).strip()
            if source_name and alias_name:
                cleaned[source_name] = alias_name
        return cleaned
