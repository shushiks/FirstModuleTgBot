from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from starlette.responses import Response

from zero_semester.admin.deps import DbSession
from zero_semester.models import AdminUser
from zero_semester.security import sign_payload, verify_password

router = APIRouter()


def login_page(error: str | None = None) -> str:
    error_html = f'<p class="error">{error}</p>' if error else ""
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Вход</title></head>
<body><main><h1>Нулевой семестр</h1>{error_html}
<form method="post"><label>Логин <input name="username" required></label><br>
<label>Пароль <input name="password" type="password" required></label><br>
<button type="submit">Войти</button></form></main></body></html>"""


@router.get("/login", response_class=HTMLResponse)
async def get_login() -> str:
    return login_page()


@router.post("/login")
async def post_login(
    request: Request,
    session: DbSession,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    admin = await session.scalar(select(AdminUser).where(AdminUser.username == username.strip()))
    if admin is None or not admin.is_active or not verify_password(admin.password_hash, password):
        return HTMLResponse(login_page("Неверный логин или пароль"), status_code=400)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "admin_session",
        sign_payload({"admin_id": admin.id}),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("admin_session")
    return response
