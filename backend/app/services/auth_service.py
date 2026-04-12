from __future__ import annotations

import time

from app.core.config import Settings
from app.persistence.repositories.app_setting_repository import AppSettingRepository
from app.security.auth import create_token, hash_password, verify_password, verify_token


class AuthService:
    KEY_ADMIN_PASSWORD_HASH = "admin_password_hash"
    KEY_ADMIN_USERNAME = "admin_username"
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "Alex1234"

    def __init__(self, repository: AppSettingRepository, app_settings: Settings) -> None:
        self.repository = repository
        self.app_settings = app_settings

    def ensure_bootstrap(self) -> None:
        username_row = self.repository.get(self.KEY_ADMIN_USERNAME)
        if username_row is None or not username_row.value.strip():
            self.repository.set(self.KEY_ADMIN_USERNAME, self.DEFAULT_ADMIN_USERNAME, "Admin username")

        hash_row = self.repository.get(self.KEY_ADMIN_PASSWORD_HASH)
        if hash_row is None or not hash_row.value.strip():
            self.repository.set(
                self.KEY_ADMIN_PASSWORD_HASH,
                hash_password(self.DEFAULT_ADMIN_PASSWORD),
                "Admin password hash",
            )

    def current_username(self) -> str:
        self.ensure_bootstrap()
        username_row = self.repository.get(self.KEY_ADMIN_USERNAME)
        if not username_row or not username_row.value.strip():
            return self.DEFAULT_ADMIN_USERNAME
        return username_row.value.strip()

    def password_is_set(self) -> bool:
        self.ensure_bootstrap()
        hash_row = self.repository.get(self.KEY_ADMIN_PASSWORD_HASH)
        return bool(hash_row and hash_row.value.strip())

    def authenticate(self, username: str, password: str) -> tuple[str, int] | None:
        self.ensure_bootstrap()
        current_username = self.current_username()
        if username.strip() != current_username:
            return None

        hash_row = self.repository.get(self.KEY_ADMIN_PASSWORD_HASH)
        if hash_row is None or not verify_password(password, hash_row.value):
            return None

        expires_in = 60 * 60 * 12
        token = create_token(
            secret=self.app_settings.auth_secret,
            subject=current_username,
            expires_in_seconds=expires_in,
        )
        return token, int(time.time()) + expires_in

    def change_password(self, *, current_password: str, new_password: str) -> bool:
        self.ensure_bootstrap()
        hash_row = self.repository.get(self.KEY_ADMIN_PASSWORD_HASH)
        if hash_row is None or not verify_password(current_password, hash_row.value):
            return False

        self.repository.set(self.KEY_ADMIN_PASSWORD_HASH, hash_password(new_password), "Admin password hash")
        return True

    def verify_access_token(self, token: str) -> str | None:
        payload = verify_token(token, secret=self.app_settings.auth_secret)
        if payload is None:
            return None
        return payload.sub
