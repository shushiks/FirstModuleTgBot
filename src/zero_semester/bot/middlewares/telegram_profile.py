from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser

from zero_semester.database import session_factory
from zero_semester.repositories.users import UserRepository


class TelegramProfileMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user = data.get("event_from_user")
        if isinstance(telegram_user, TelegramUser):
            async with session_factory() as session:
                repository = UserRepository(session)
                user = await repository.get_by_telegram_id(telegram_user.id)
                if user is not None:
                    user.last_activity_at = datetime.now()
                    if user.telegram_username != telegram_user.username:
                        await repository.set_telegram_username(user, telegram_user.username)
                    await session.commit()
        return await handler(event, data)
