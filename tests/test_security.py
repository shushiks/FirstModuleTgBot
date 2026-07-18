from zero_semester.security import sign_payload, verify_payload


def test_signed_payload_round_trip() -> None:
    token = sign_payload({"user_id": 10, "module_id": 7})
    assert verify_payload(token) == {"user_id": 10, "module_id": 7}


def test_modified_payload_is_rejected() -> None:
    token = sign_payload({"user_id": 10})
    assert verify_payload(f"x{token}") is None
