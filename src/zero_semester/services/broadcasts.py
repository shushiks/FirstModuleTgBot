from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import Broadcast, BroadcastRecipient, User
from zero_semester.models.enums import BroadcastStatus


async def create_broadcast(
    session: AsyncSession,
    *,
    title: str,
    text: str,
    button_text: str | None,
    button_url: str | None,
    school_id: int | None,
    scheduled_at: datetime | None,
) -> Broadcast:
    broadcast = Broadcast(
        title=title,
        text=text,
        button_text=button_text,
        button_url=button_url,
        school_id=school_id,
        scheduled_at=scheduled_at,
        status=BroadcastStatus.SCHEDULED if scheduled_at else BroadcastStatus.DRAFT,
    )
    session.add(broadcast)
    await session.flush()

    if scheduled_at is not None:
        statement = select(User.id).where(User.is_blocked.is_(False))
        if school_id is not None:
            statement = statement.where(User.school_id == school_id)
        user_ids = list((await session.scalars(statement)).all())
        session.add_all(
            [BroadcastRecipient(broadcast_id=broadcast.id, user_id=user_id) for user_id in user_ids]
        )
        if not user_ids:
            broadcast.status = BroadcastStatus.COMPLETED
    await session.commit()
    return broadcast


async def update_draft_broadcast(
    session: AsyncSession,
    broadcast: Broadcast,
    *,
    title: str,
    text: str,
    button_text: str | None,
    button_url: str | None,
    school_id: int | None,
    scheduled_at: datetime | None,
) -> Broadcast:
    if broadcast.status != BroadcastStatus.DRAFT:
        raise ValueError("Редактировать можно только черновик")
    broadcast.title = title
    broadcast.text = text
    broadcast.button_text = button_text
    broadcast.button_url = button_url
    broadcast.school_id = school_id
    broadcast.scheduled_at = scheduled_at
    if scheduled_at is not None:
        broadcast.status = BroadcastStatus.SCHEDULED
        statement = select(User.id).where(User.is_blocked.is_(False))
        if school_id is not None:
            statement = statement.where(User.school_id == school_id)
        user_ids = list((await session.scalars(statement)).all())
        session.add_all(
            [BroadcastRecipient(broadcast_id=broadcast.id, user_id=user_id) for user_id in user_ids]
        )
        if not user_ids:
            broadcast.status = BroadcastStatus.COMPLETED
    await session.commit()
    return broadcast
