from fastapi import APIRouter, Request
from sqlalchemy import func, select
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.templating import render_template
from zero_semester.models import Broadcast, Module, SupportTicket, User
from zero_semester.models.enums import BroadcastStatus, PublicationStatus, TicketStatus

router = APIRouter()


@router.get("/")
async def dashboard(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    metrics = {
        "users": await session.scalar(select(func.count()).select_from(User)) or 0,
        "draft_modules": await session.scalar(
            select(func.count()).select_from(Module).where(
                Module.status == PublicationStatus.DRAFT
            )
        )
        or 0,
        "open_tickets": await session.scalar(
            select(func.count()).select_from(SupportTicket).where(
                SupportTicket.status != TicketStatus.CLOSED
            )
        )
        or 0,
        "draft_broadcasts": await session.scalar(
            select(func.count()).select_from(Broadcast).where(
                Broadcast.status == BroadcastStatus.DRAFT
            )
        )
        or 0,
    }
    return render_template(
        request,
        "dashboard.html",
        {
            "admin": admin,
            "metrics": metrics,
            "forbidden": request.query_params.get("forbidden") == "1",
        },
    )
