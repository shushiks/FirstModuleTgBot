from fastapi.testclient import TestClient

from zero_semester.admin.main import app


def test_liveness() -> None:
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_page() -> None:
    response = TestClient(app).get("/login")
    assert response.status_code == 200
    assert "Нулевой семестр" in response.text
