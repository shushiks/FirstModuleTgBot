from dataclasses import dataclass
from urllib.parse import quote_plus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.sql.elements import ColumnElement
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.forms import UserSchoolForm
from zero_semester.admin.templating import render_template
from zero_semester.models import AuditLog, School, User
from zero_semester.models.enums import AdminRole

router = APIRouter(prefix="/users", tags=["users"])


@dataclass(frozen=True, slots=True)
class TelegramProfile:
    label: str
    url: str
    username: str | None


def _fallback_profile(
    telegram_id: int,
    username: str | None = None,
) -> TelegramProfile:
    if username:
        return TelegramProfile(
            label=f"@{username}",
            url=f"https://t.me/{username}",
            username=username,
        )
    return TelegramProfile(
        label="Открыть в Telegram",
        url=f"tg://user?id={telegram_id}",
        username=None,
    )


def _telegram_profiles(
    users: list[User],
) -> dict[int, TelegramProfile]:
    return {
        user.telegram_id: _fallback_profile(user.telegram_id, user.telegram_username)
        for user in users
    }


async def _users_context(
    session: DbSession,
    admin: CurrentAdmin,
    *,
    query: str = "",
) -> dict[str, object]:
    statement = (
        select(User, School.name)
        .join(School, School.id == User.school_id)
        .order_by(User.created_at.desc())
        .limit(100)
    )
    if query:
        username_query = query.removeprefix("@").strip()
        search_filter: ColumnElement[bool] = or_(
            User.time_login.ilike(f"%{query}%"),
            User.telegram_username.ilike(f"%{username_query}%"),
        )
        telegram_id_query = query.removeprefix("+")
        if telegram_id_query.isdigit():
            search_filter = or_(
                search_filter,
                User.telegram_id == int(telegram_id_query),
            )
        statement = statement.where(search_filter)
    rows = (
        await session.execute(statement)
    ).all()
    schools = list((await session.scalars(select(School).order_by(School.name))).all())
    users = [user for user, _ in rows]
    telegram_profiles = _telegram_profiles(users)
    return {
        "admin": admin,
        "rows": rows,
        "schools": schools,
        "telegram_profiles": telegram_profiles,
        "query": query,
    }


@router.get("")
async def users_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    query = request.query_params.get("q", "").strip()[:128]
    context = await _users_context(session, admin, query=query)
    context["school_updated"] = request.query_params.get("school_updated") == "1"
    return render_template(request, "users/index.html", context)


@router.post("/{user_id}/school")
async def change_user_school(
    request: Request,
    user_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    if admin.role not in {AdminRole.ADMIN, AdminRole.CONTENT_MANAGER}:
        raise HTTPException(status_code=403, detail="Недостаточно прав для смены школы")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    try:
        raw = dict(await request.form())
        return_query = str(raw.pop("return_query", "")).strip()[:128]
        form = UserSchoolForm.model_validate(raw)
        school = await session.get(School, form.school_id)
        if school is None:
            raise ValueError("Школа не найдена")

        old_school_id = user.school_id
        if old_school_id != school.id:
            user.school_id = school.id
            session.add(
                AuditLog(
                    admin_user_id=admin.id,
                    action="user.school_changed",
                    entity_type="user",
                    entity_id=str(user.id),
                    changes={
                        "old_school_id": old_school_id,
                        "new_school_id": school.id,
                    },
                )
            )
            await session.commit()
    except (ValidationError, ValueError) as error:
        await session.rollback()
        context = await _users_context(session, admin, query=return_query)
        context["error"] = f"Не удалось сменить школу: {error}"
        return render_template(request, "users/index.html", context, status_code=400)

    redirect_url = "/users?school_updated=1"
    if return_query:
        redirect_url += f"&q={quote_plus(return_query)}"
    return RedirectResponse(redirect_url, status_code=303)
