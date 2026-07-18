import asyncio
import logging

from aiogram import Bot, Dispatcher

from zero_semester.bot.handlers import routers
from zero_semester.config import get_settings


async def run() -> None:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    dispatcher = Dispatcher()
    for router in routers:
        dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
