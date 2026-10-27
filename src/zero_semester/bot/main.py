import asyncio

from aiogram import Bot, Dispatcher

from zero_semester.bot.handlers import routers
from zero_semester.bot.middlewares import TelegramProfileMiddleware
from zero_semester.config import get_settings
from zero_semester.logging_config import configure_logging


async def run() -> None:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    dispatcher = Dispatcher()
    profile_middleware = TelegramProfileMiddleware()
    dispatcher.message.outer_middleware(profile_middleware)
    dispatcher.callback_query.outer_middleware(profile_middleware)
    for router in routers:
        dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


def main() -> None:
    configure_logging("bot")
    asyncio.run(run())


if __name__ == "__main__":
    main()
