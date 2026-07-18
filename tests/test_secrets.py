from zero_semester.services.secrets import normalize_secret


def test_secret_is_trimmed_and_case_insensitive() -> None:
    assert normalize_secret("  Ключ 42  ") == "ключ 42"
