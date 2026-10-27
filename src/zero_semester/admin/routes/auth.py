from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from starlette.responses import Response

from zero_semester.admin.auth import authenticate_admin
from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.forms import LoginForm
from zero_semester.admin.templating import render_template
from zero_semester.config import get_settings
from zero_semester.security import csrf_tokens_match, new_csrf_token, sign_payload

router = APIRouter()


@router.get("/login")
async def get_login(request: Request) -> Response:
    return render_template(request, "login.html")


@router.post("/login")
async def post_login(
    request: Request,
    session: DbSession,
) -> Response:
    try:
        raw_form = dict(await request.form())
        raw_csrf_token = raw_form.get("csrf_token")
        if not csrf_tokens_match(
            request.cookies.get("csrf_token"),
            raw_csrf_token if isinstance(raw_csrf_token, str) else None,
        ):
            return render_template(
                request,
                "login.html",
                {"error": "Форма устарела. Обнови страницу и повтори вход"},
                status_code=403,
            )
        form = LoginForm.model_validate(raw_form)
    except ValidationError:
        return render_template(
            request, "login.html", {"error": "Заполни логин и пароль"}, status_code=400
        )
    admin = await authenticate_admin(session, username=form.username, password=form.password)
    if admin is None:
        return render_template(
            request, "login.html", {"error": "Неверный логин или пароль"}, status_code=400
        )
    response = RedirectResponse("/", status_code=303)
    settings = get_settings()
    is_secure = settings.app_env not in {"local", "test"} or request.url.scheme == "https"
    response.set_cookie(
        "admin_session",
        sign_payload(
            {"admin_id": admin.id},
            purpose="admin_session",
            ttl_seconds=12 * 60 * 60,
        ),
        httponly=True,
        samesite="strict",
        secure=is_secure,
        max_age=12 * 60 * 60,
    )
    csrf_token = new_csrf_token()
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        max_age=12 * 60 * 60,
    )
    return response


@router.post("/logout")
async def logout(_admin: CurrentAdmin) -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("admin_session")
    response.delete_cookie("csrf_token")
    return response
