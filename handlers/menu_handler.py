"""
menu_handler.py
Tuzatishlar:
- send_main_menu(bot, chat_id, user_id) — bot obyekti bilan ishlaydi
- show_main_menu(message, user_id) — eski interfeysni saqlaydi
"""

import logging
from aiogram import Router, Bot, F
from aiogram.types import Message

from database import get_user, is_premium
from keyboards import kb_main_menu

logger = logging.getLogger(__name__)
router = Router()


async def send_main_menu(bot: Bot, chat_id: int, user_id: int):
    """Bot + chat_id bilan asosiy menyuni yuborish (callback'lardan chaqirish uchun)"""
    user = await get_user(user_id)
    premium = await is_premium(user_id)

    if not user:
        await bot.send_message(chat_id=chat_id, text="❗ Xato yuz berdi. /start bosing.")
        return

    gender_emoji = "👦" if user.get("gender") == "male" else "👧"
    premium_badge = "⭐ Premium" if premium else "🆓 Tekin"

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🏠 <b>Asosiy menyu</b>\n\n"
            f"{gender_emoji} {user.get('display_name', 'Foydalanuvchi')} | "
            f"🔢 {user.get('age', '?')} yosh | "
            f"📍 {user.get('region', '—')}\n"
            f"💎 Holat: {premium_badge}\n\n"
            f"Nima qilmoqchisiz?"
        ),
        reply_markup=kb_main_menu(is_premium_user=premium)
    )


async def show_main_menu(message: Message, user_id: int):
    """Message obyekti bilan asosiy menyuni yuborish"""
    await send_main_menu(message.bot, message.chat.id, user_id)


@router.message(F.text == "🏠 Asosiy menyu")
async def main_menu_handler(message: Message):
    await show_main_menu(message, message.from_user.id)
