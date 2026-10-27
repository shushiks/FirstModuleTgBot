import pytest

from zero_semester.services.registration import RegistrationError, normalize_time_login


@pytest.mark.parametrize(
    "value",
    ["a.ivanov10", "anna.ivanova21?", "mikha.a.ivanov", "@e.p.kuznetsov"],
)
def test_time_login_accepts_real_world_formats(value: str) -> None:
    assert normalize_time_login(f"  {value}  ") == value


def test_time_login_rejects_empty_value() -> None:
    with pytest.raises(RegistrationError):
        normalize_time_login("   ")
