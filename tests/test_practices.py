import pytest

from zero_semester.services.practice import PracticeError, ensure_attempt_available


def test_next_practice_attempt() -> None:
    assert ensure_attempt_available(completed_attempts=0, max_attempts=2) == 1
    assert ensure_attempt_available(completed_attempts=1, max_attempts=2) == 2


def test_practice_attempt_limit() -> None:
    with pytest.raises(PracticeError, match="Попытки закончились"):
        ensure_attempt_available(completed_attempts=2, max_attempts=2)
