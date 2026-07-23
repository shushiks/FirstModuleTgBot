from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.forms import SecretKeyForm
from zero_semester.admin.templating import render_template
from zero_semester.models import LmsCourse, Module, ModuleLmsCourse, School, SecretKey
from zero_semester.services.secrets import activate_secret_key

router = APIRouter(prefix="/keys", tags=["keys"])


async def _keys_context(session: DbSession, admin: CurrentAdmin) -> dict[str, object]:
    courses = list(
        (
            await session.execute(
                select(LmsCourse, School, Module)
                .join(School, School.id == LmsCourse.school_id)
                .outerjoin(ModuleLmsCourse, ModuleLmsCourse.lms_course_id == LmsCourse.id)
                .outerjoin(Module, Module.id == ModuleLmsCourse.module_id)
                .order_by(School.name, LmsCourse.name)
            )
        ).all()
    )
    keys = list(
        (
            await session.execute(
                select(SecretKey, LmsCourse, School, Module)
                .join(LmsCourse, LmsCourse.id == SecretKey.lms_course_id)
                .join(School, School.id == LmsCourse.school_id)
                .outerjoin(ModuleLmsCourse, ModuleLmsCourse.lms_course_id == LmsCourse.id)
                .outerjoin(Module, Module.id == ModuleLmsCourse.module_id)
                .order_by(SecretKey.created_at.desc())
            )
        ).all()
    )
    return {"admin": admin, "courses": courses, "keys": keys}


@router.get("")
async def keys_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    return render_template(request, "keys/index.html", await _keys_context(session, admin))


@router.post("")
async def create_key(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    try:
        form = SecretKeyForm.model_validate(dict(await request.form()))
        lms_course = await session.get(LmsCourse, form.lms_course_id)
        if lms_course is None:
            raise ValueError("LMS-курс не найден")
        await activate_secret_key(
            session,
            lms_course_id=lms_course.id,
            value=form.value,
            label=form.label,
        )
        await session.commit()
    except (ValidationError, ValueError, IntegrityError) as error:
        await session.rollback()
        context = await _keys_context(session, admin)
        context["error"] = f"Не удалось сохранить ключ: {error}"
        return render_template(request, "keys/index.html", context, status_code=400)
    return RedirectResponse("/keys", status_code=303)


@router.post("/{key_id}/toggle")
async def toggle_key(
    key_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> RedirectResponse:
    key = await session.get(SecretKey, key_id)
    if key is not None:
        if key.is_active:
            key.is_active = False
        else:
            await session.execute(
                update(SecretKey)
                .where(
                    SecretKey.lms_course_id == key.lms_course_id,
                    SecretKey.id != key.id,
                    SecretKey.is_active.is_(True),
                )
                .values(is_active=False)
            )
            key.is_active = True
        await session.commit()
    return RedirectResponse("/keys", status_code=303)
