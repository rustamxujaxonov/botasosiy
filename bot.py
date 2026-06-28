"""
bot.py — Asosiy ishga tushirish fayli
Tuzatishlar:
- Railway restart'da FSM yo'qolmasligi uchun RedisStorage (REDIS_URL bo'lsa)
- Graceful shutdown
- Yaxshi error logging
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import referral_handler
dp.include_router(referral_handler.router)
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
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def get_storage():
    """
    REDIS_URL environment variable bo'lsa — RedisStorage ishlatiladi.
    Aks holda MemoryStorage (restart'da FSM yo'qoladi, lekin ishlaydi).
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(redis_url)
            logger.info("✅ RedisStorage ulandi")
            return storage
        except ImportError:
            logger.warning("⚠️ aiogram[redis] o'rnatilmagan, MemoryStorage ishlatilmoqda")
        except Exception as e:
            logger.warning(f"⚠️ Redis ulanmadi ({e}), MemoryStorage ishlatilmoqda")
    else:
        logger.info("ℹ️ REDIS_URL yo'q — MemoryStorage ishlatilmoqda")
    return MemoryStorage()


async def main():
    # DB ni ishga tushirish
    await init_db()

    # Bot va Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=get_storage())

    # Router'larni tartib bilan qo'shish (muhim: admin birinchi)
    dp.include_router(admin_handler.router)
    dp.include_router(start_handler.router)
    dp.include_router(registration_handler.router)
    dp.include_router(premium_handler.router)
    dp.include_router(profile_handler.router)
    dp.include_router(search_handler.router)
    dp.include_router(chat_handler.router)
    dp.include_router(menu_handler.router)

    logger.info("🚀 Bot ishga tushdi!")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Restart paytidagi eski xabarlarni o'tkazib yuborish
        )
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
