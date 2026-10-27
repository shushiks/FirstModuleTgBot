from fastapi.testclient import TestClient

from zero_semester.admin.main import app
from zero_semester.admin.routes.analytics import (
    csv_response,
    format_event_properties,
    safe_csv_cell,
)


def test_liveness() -> None:
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_page() -> None:
    response = TestClient(app).get("/login")
    assert response.status_code == 200
    assert "Нулевой семестр" in response.text
    assert "/static/admin.css" in response.text
    assert 'name="csrf_token"' in response.text
    assert response.cookies.get("csrf_token")


def test_internal_api_documentation_is_hidden() -> None:
    client = TestClient(app)
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_security_headers_are_present() -> None:
    response = TestClient(app).get("/login")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_login_post_without_csrf_is_rejected() -> None:
    response = TestClient(app).post(
        "/login",
        data={"username": "admin", "password": "not-the-real-password"},
    )
    assert response.status_code == 403


def test_oversized_request_is_rejected_before_body_parsing() -> None:
    response = TestClient(app).post(
        "/login",
        headers={"content-length": str(56 * 1024 * 1024)},
    )
    assert response.status_code == 413


def test_admin_css_is_mounted() -> None:
    response = TestClient(app).get("/static/admin.css")
    assert response.status_code == 200
    assert "--accent" in response.text


def test_admin_section_requires_login() -> None:
    response = TestClient(app).get("/content")
    assert response.status_code == 401


def test_browser_is_redirected_to_login() -> None:
    response = TestClient(app).get(
        "/",
        headers={"accept": "text/html"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_browser_forbidden_response_is_redirected_to_dashboard() -> None:
    from starlette.exceptions import HTTPException

    from zero_semester.admin.main import admin_http_exception_handler

    request = TestClient(app).build_request(
        "GET",
        "/content",
        headers={"accept": "text/html"},
    )
    response = __import__("asyncio").run(
        admin_http_exception_handler(request, HTTPException(status_code=403))
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?forbidden=1"


def test_analytics_exports_require_login() -> None:
    client = TestClient(app)
    assert client.get("/analytics/export/users.csv").status_code == 401
    assert client.get("/analytics/export/events.csv").status_code == 401


def test_csv_response_has_bom_and_download_header() -> None:
    response = csv_response("report.csv", ["ключ"], [["значение"]])
    assert response.body.startswith(b"\xef\xbb\xbf")
    assert "ключ".encode() in response.body
    assert response.headers["content-disposition"] == 'attachment; filename="report.csv"'


def test_csv_formula_is_neutralized() -> None:
    assert safe_csv_cell("=HYPERLINK('https://example.test')") == (
        "'=HYPERLINK('https://example.test')"
    )
    assert safe_csv_cell("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert safe_csv_cell("обычный текст") == "обычный текст"


def test_event_properties_are_exported_as_readable_text() -> None:
    assert format_event_properties(
        {"practice_id": 7, "correct": False},
        practice_questions={7: "Что изменилось?"},
    ) == (
        "Вопрос: Что изменилось?; Результат: неверно"
    )
    assert format_event_properties({"reason": "expired"}) == (
        "Причина: срок действия ключа истёк"
    )
