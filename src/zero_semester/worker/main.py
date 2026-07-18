import asyncio
import logging

from aiogram import Bot

from zero_semester.config import get_settings
from zero_semester.database import session_factory
from zero_semester.worker.tasks import send_due_broadcasts

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(settings.telegram_bot_token.get_secret_value())
    try:
        while True:
            async with session_factory() as session:
                sent = await send_due_broadcasts(session, bot)
            if sent:
                logger.info("Sent %s broadcast messages", sent)
            await asyncio.sleep(5)
    finally:
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
