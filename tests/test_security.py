import zero_semester.security as security
from zero_semester.security import csrf_tokens_match, sign_payload, verify_payload


def test_signed_payload_round_trip() -> None:
    token = sign_payload(
        {"user_id": 10, "module_id": 7},
        purpose="test",
        ttl_seconds=60,
    )
    assert verify_payload(token, expected_purpose="test") == {"user_id": 10, "module_id": 7}


def test_modified_payload_is_rejected() -> None:
    token = sign_payload({"user_id": 10}, purpose="test", ttl_seconds=60)
    assert verify_payload(f"x{token}", expected_purpose="test") is None


def test_signed_payload_cannot_be_used_for_another_purpose() -> None:
    token = sign_payload({"admin_id": 1}, purpose="admin_session", ttl_seconds=60)
    assert verify_payload(token, expected_purpose="lms_click") is None


def test_expired_payload_is_rejected(monkeypatch: object) -> None:
    now = 1_700_000_000
    monkeypatch.setattr(security.time, "time", lambda: now)  # type: ignore[attr-defined]
    token = sign_payload({"admin_id": 1}, purpose="admin_session", ttl_seconds=60)
    monkeypatch.setattr(security.time, "time", lambda: now + 61)  # type: ignore[attr-defined]
    assert verify_payload(token, expected_purpose="admin_session") is None


def test_csrf_tokens_must_be_present_and_equal() -> None:
    assert csrf_tokens_match("same", "same")
    assert not csrf_tokens_match("cookie", "form")
    assert not csrf_tokens_match(None, None)
