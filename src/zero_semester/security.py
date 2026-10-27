import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from zero_semester.config import get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def sign_payload(
    payload: dict[str, Any],
    *,
    purpose: str,
    ttl_seconds: int,
) -> str:
    now = int(time.time())
    signed_payload = {
        **payload,
        "_purpose": purpose,
        "_issued_at": now,
        "_expires_at": now + ttl_seconds,
        "_nonce": secrets.token_urlsafe(16),
    }
    raw = json.dumps(signed_payload, separators=(",", ":"), sort_keys=True).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=")
    secret = get_settings().app_secret_key.get_secret_value().encode()
    signature = hmac.new(secret, encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def verify_payload(token: str, *, expected_purpose: str) -> dict[str, Any] | None:
    try:
        encoded_text, signature_text = token.split(".", 1)
        encoded = encoded_text.encode()
        padding = b"=" * (-len(signature_text) % 4)
        signature = base64.urlsafe_b64decode(signature_text.encode() + padding)
        secret = get_settings().app_secret_key.get_secret_value().encode()
        expected = hmac.new(secret, encoded, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload_padding = b"=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + payload_padding))
        if not isinstance(payload, dict):
            return None
        now = int(time.time())
        issued_at = payload.get("_issued_at")
        expires_at = payload.get("_expires_at")
        if (
            payload.get("_purpose") != expected_purpose
            or not isinstance(issued_at, int)
            or not isinstance(expires_at, int)
            or issued_at > now + 60
            or expires_at <= now
            or expires_at <= issued_at
        ):
            return None
        return {key: value for key, value in payload.items() if not key.startswith("_")}
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_tokens_match(cookie_token: str | None, form_token: str | None) -> bool:
    if not cookie_token or not form_token:
        return False
    return hmac.compare_digest(cookie_token, form_token)
