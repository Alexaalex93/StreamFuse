from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def hash_password(password: str, *, iterations: int = 200_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations_raw, salt_raw, digest_raw = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(digest_raw)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


@dataclass(slots=True)
class TokenPayload:
    sub: str
    exp: int


def create_token(*, secret: str, subject: str, expires_in_seconds: int = 60 * 60 * 12) -> str:
    now = int(time.time())
    payload = {"sub": subject, "exp": now + expires_in_seconds}
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_part = _b64url_encode(payload_raw)
    sig = hmac.new(secret.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    sig_part = _b64url_encode(sig)
    return f"{payload_part}.{sig_part}"


def verify_token(token: str, *, secret: str) -> TokenPayload | None:
    try:
        payload_part, sig_part = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(secret.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    try:
        supplied_sig = _b64url_decode(sig_part)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, supplied_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
        sub = str(payload["sub"])
        exp = int(payload["exp"])
    except Exception:
        return None

    if exp <= int(time.time()):
        return None
    return TokenPayload(sub=sub, exp=exp)
