from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.forms import BroadcastForm
from zero_semester.admin.templating import render_template
from zero_semester.config import get_settings
from zero_semester.models import Broadcast, School
from zero_semester.services.broadcasts import (
    create_broadcast as create_broadcast_service,
)
from zero_semester.services.broadcasts import update_draft_broadcast

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


async def broadcasts_context(session: DbSession, admin: CurrentAdmin) -> dict[str, object]:
    broadcasts = list(
        (await session.scalars(select(Broadcast).order_by(Broadcast.created_at.desc()))).all()
    )
    schools = list((await session.scalars(select(School).order_by(School.name))).all())
    return {"admin": admin, "broadcasts": broadcasts, "schools": schools}


@router.get("")
async def broadcasts_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    return render_template(
        request, "broadcasts/index.html", await broadcasts_context(session, admin)
    )


@router.post("")
async def create_broadcast(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    try:
        form = BroadcastForm.model_validate(dict(await request.form()))
        scheduled_at = form.scheduled_at
        if form.action == "send_now":
            scheduled_at = datetime.now(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)
        elif form.action == "schedule" and scheduled_at is None:
            raise ValueError("Укажи дату и время для запланированной рассылки")
        elif form.action == "draft":
            scheduled_at = None
    except ValidationError as error:
        context = await broadcasts_context(session, admin)
        context["error"] = f"Проверь поля рассылки: {error}"
        return render_template(request, "broadcasts/index.html", context, status_code=400)
    except ValueError as error:
        context = await broadcasts_context(session, admin)
        context["error"] = str(error)
        return render_template(request, "broadcasts/index.html", context, status_code=400)
    await create_broadcast_service(
        session,
        title=form.title,
        text=form.text,
        button_text=form.button_text,
        button_url=str(form.button_url) if form.button_url is not None else None,
        school_id=form.school_id,
        scheduled_at=scheduled_at,
    )
    return RedirectResponse("/broadcasts", status_code=303)


@router.get("/{broadcast_id}/edit")
async def edit_broadcast_page(
    request: Request,
    broadcast_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if broadcast.status.value != "draft":
        raise HTTPException(status_code=400, detail="Редактировать можно только черновик")
    schools = list((await session.scalars(select(School).order_by(School.name))).all())
    return render_template(
        request,
        "broadcasts/edit.html",
        {"admin": admin, "broadcast": broadcast, "schools": schools},
    )


@router.post("/{broadcast_id}/edit")
async def edit_broadcast(
    request: Request,
    broadcast_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    try:
        form = BroadcastForm.model_validate(dict(await request.form()))
        scheduled_at = form.scheduled_at
        if form.action == "send_now":
            scheduled_at = datetime.now(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)
        elif form.action == "schedule" and scheduled_at is None:
            raise ValueError("Укажи дату и время для запланированной рассылки")
        elif form.action == "draft":
            scheduled_at = None
        await update_draft_broadcast(
            session,
            broadcast,
            title=form.title,
            text=form.text,
            button_text=form.button_text,
            button_url=str(form.button_url) if form.button_url is not None else None,
            school_id=form.school_id,
            scheduled_at=scheduled_at,
        )
    except (ValidationError, ValueError) as error:
        await session.rollback()
        schools = list((await session.scalars(select(School).order_by(School.name))).all())
        return render_template(
            request,
            "broadcasts/edit.html",
            {
                "admin": admin,
                "broadcast": broadcast,
                "schools": schools,
                "error": f"Не удалось сохранить: {error}",
            },
            status_code=400,
        )
    return RedirectResponse("/broadcasts", status_code=303)
