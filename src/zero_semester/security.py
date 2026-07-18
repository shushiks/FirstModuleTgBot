import base64
import hashlib
import hmac
import json
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


def sign_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=")
    secret = get_settings().app_secret_key.get_secret_value().encode()
    signature = hmac.new(secret, encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def verify_payload(token: str) -> dict[str, Any] | None:
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
        return payload if isinstance(payload, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
