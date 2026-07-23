from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from zero_semester.config import get_settings
from zero_semester.models import Broadcast, BroadcastRecipient, User
from zero_semester.models.enums import BroadcastStatus, DeliveryStatus


async def send_due_broadcasts(session: AsyncSession, bot: Bot, batch_size: int = 30) -> int:
    local_now = datetime.now(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)
    statement = (
        select(BroadcastRecipient, Broadcast, User)
        .join(Broadcast, Broadcast.id == BroadcastRecipient.broadcast_id)
        .join(User, User.id == BroadcastRecipient.user_id)
        .where(
            BroadcastRecipient.status == DeliveryStatus.PENDING,
            Broadcast.status.in_([BroadcastStatus.SCHEDULED, BroadcastStatus.SENDING]),
            Broadcast.scheduled_at <= local_now,
            User.is_blocked.is_(False),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
    )
    rows = (await session.execute(statement)).all()
    sent = 0
    touched_broadcasts: dict[int, Broadcast] = {}
    for recipient, broadcast, user in rows:
        touched_broadcasts[broadcast.id] = broadcast
        broadcast.status = BroadcastStatus.SENDING
        try:
            keyboard = None
            if broadcast.button_text and broadcast.button_url:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=broadcast.button_text,
                                url=broadcast.button_url,
                            )
                        ]
                    ]
                )
            await bot.send_message(user.telegram_id, broadcast.text, reply_markup=keyboard)
        except Exception as error:  # Telegram errors are stored per recipient.
            recipient.status = DeliveryStatus.FAILED
            recipient.error = str(error)[:2000]
        else:
            recipient.status = DeliveryStatus.SENT
            recipient.sent_at = local_now
            sent += 1
    await session.flush()
    for broadcast_id, broadcast in touched_broadcasts.items():
        pending = await session.scalar(
            select(func.count())
            .select_from(BroadcastRecipient)
            .where(
                BroadcastRecipient.broadcast_id == broadcast_id,
                BroadcastRecipient.status == DeliveryStatus.PENDING,
            )
        )
        if not pending:
            broadcast.status = BroadcastStatus.COMPLETED
    await session.commit()
    return sent
