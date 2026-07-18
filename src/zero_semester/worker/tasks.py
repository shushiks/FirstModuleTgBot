from datetime import UTC, datetime

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.models import Broadcast, BroadcastRecipient, User
from zero_semester.models.enums import BroadcastStatus, DeliveryStatus


async def send_due_broadcasts(session: AsyncSession, bot: Bot, batch_size: int = 30) -> int:
    statement = (
        select(BroadcastRecipient, Broadcast, User)
        .join(Broadcast, Broadcast.id == BroadcastRecipient.broadcast_id)
        .join(User, User.id == BroadcastRecipient.user_id)
        .where(
            BroadcastRecipient.status == DeliveryStatus.PENDING,
            Broadcast.status.in_([BroadcastStatus.SCHEDULED, BroadcastStatus.SENDING]),
            Broadcast.scheduled_at <= datetime.now(UTC),
            User.is_blocked.is_(False),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
    )
    rows = (await session.execute(statement)).all()
    sent = 0
    for recipient, broadcast, user in rows:
        broadcast.status = BroadcastStatus.SENDING
        try:
            await bot.send_message(user.telegram_id, broadcast.text)
        except Exception as error:  # Telegram errors are stored per recipient.
            recipient.status = DeliveryStatus.FAILED
            recipient.error = str(error)[:2000]
        else:
            recipient.status = DeliveryStatus.SENT
            recipient.sent_at = datetime.now(UTC)
            sent += 1
    await session.commit()
    return sent
