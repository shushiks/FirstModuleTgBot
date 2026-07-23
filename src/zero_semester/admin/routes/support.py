from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.templating import render_template
from zero_semester.config import get_settings
from zero_semester.models import SupportMessage, SupportTicket, User
from zero_semester.models.enums import TicketStatus

router = APIRouter(prefix="/support", tags=["support"])


@router.get("")
async def support_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    rows = (
        await session.execute(
            select(
                SupportTicket,
                User.telegram_id,
                User.telegram_username,
                User.time_login,
                func.count(SupportMessage.id),
            )
            .join(User, User.id == SupportTicket.user_id)
            .outerjoin(SupportMessage, SupportMessage.ticket_id == SupportTicket.id)
            .group_by(SupportTicket.id, User.id)
            .order_by(SupportTicket.created_at.desc())
        )
    ).all()
    metrics = {
        "new": sum(ticket.status == TicketStatus.NEW for ticket, *_ in rows),
        "in_progress": sum(
            ticket.status == TicketStatus.IN_PROGRESS for ticket, *_ in rows
        ),
        "closed": sum(ticket.status == TicketStatus.CLOSED for ticket, *_ in rows),
    }
    return render_template(
        request,
        "support/index.html",
        {"admin": admin, "rows": rows, "metrics": metrics},
    )


@router.get("/{ticket_id}")
async def support_ticket_page(
    request: Request,
    ticket_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    row = (
        await session.execute(
            select(SupportTicket, User)
            .join(User, User.id == SupportTicket.user_id)
            .where(SupportTicket.id == ticket_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    messages = list(
        (
            await session.scalars(
                select(SupportMessage)
                .where(SupportMessage.ticket_id == ticket_id)
                .order_by(SupportMessage.created_at)
            )
        ).all()
    )
    return render_template(
        request,
        "support/detail.html",
        {"admin": admin, "ticket": row[0], "user": row[1], "messages": messages},
    )


@router.post("/{ticket_id}/reply")
async def reply_to_support_ticket(
    request: Request,
    ticket_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> Response:
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    user = await session.get(User, ticket.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    text = str((await request.form()).get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Ответ не может быть пустым")
    token = get_settings().telegram_bot_token
    if token is None:
        raise HTTPException(status_code=503, detail="Telegram-бот не настроен")
    bot = Bot(token=token.get_secret_value())
    try:
        await bot.send_message(
            user.telegram_id,
            f"Ответ поддержки:\n\n{text}",
        )
    except TelegramAPIError as error:
        raise HTTPException(status_code=502, detail="Не удалось отправить ответ") from error
    finally:
        await bot.session.close()
    ticket.status = TicketStatus.IN_PROGRESS
    session.add(SupportMessage(ticket_id=ticket.id, sender_type="support", text=text))
    await session.commit()
    return RedirectResponse(f"/support/{ticket.id}", status_code=303)


@router.post("/{ticket_id}/close")
async def close_support_ticket(
    ticket_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> RedirectResponse:
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = datetime.now()
    await session.commit()
    return RedirectResponse(f"/support/{ticket.id}", status_code=303)
