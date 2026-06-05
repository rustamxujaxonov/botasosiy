import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import (
    start_handler,
    registration_handler,
    menu_handler,
    search_handler,
    premium_handler,
    profile_handler,
    admin_handler,
    chat_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register all routers
    dp.include_router(admin_handler.router)
    dp.include_router(start_handler.router)
    dp.include_router(registration_handler.router)
    dp.include_router(premium_handler.router)
    dp.include_router(search_handler.router)
    dp.include_router(chat_handler.router)
    dp.include_router(profile_handler.router)
    dp.include_router(menu_handler.router)

    logger.info("Bot ishga tushdi...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
