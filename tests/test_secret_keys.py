from zero_semester.services.secrets import digest_secret, normalize_secret


def test_secret_is_trimmed_and_case_insensitive() -> None:
    assert normalize_secret("  Ключ 42  ") == "ключ 42"


def test_secret_digest_is_case_insensitive_and_does_not_contain_plaintext() -> None:
    first = digest_secret("  Ключ 42  ")
    second = digest_secret("ключ 42")
    assert first == second
    assert "ключ" not in first
    assert len(first) == 64
