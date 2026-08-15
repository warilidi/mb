import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from motivation_bot.config import BOT_TOKEN
import motivation_bot.database as db
from motivation_bot.handlers import router

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")


async def start_bot() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not configured in .env")
        sys.exit(1)

    await db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Motivation bot started successfully with aiogram 3.")
    await dp.start_polling(bot)


def main():
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
