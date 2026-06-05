import logging
from aiogram import Router, F
from aiogram.types import Message

from database import get_user, is_premium
from keyboards import kb_main_menu

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message, user_id: int):
    user = await get_user(user_id)
    premium = await is_premium(user_id)

    gender_emoji = "👦" if user.get("gender") == "male" else "👧"
    premium_badge = "⭐ Premium" if premium else "🆓 Tekin"

    await message.answer(
        f"🏠 <b>Asosiy menyu</b>\n\n"
        f"{gender_emoji} {user.get('display_name', 'Foydalanuvchi')} | "
        f"🔢 {user.get('age')} yosh | "
        f"📍 {user.get('region', '—')}\n"
        f"💎 Holat: {premium_badge}\n\n"
        f"Nima qilmoqchisiz?",
        reply_markup=kb_main_menu(is_premium_user=premium),
        parse_mode="HTML"
    )


@router.message(F.text == "🏠 Asosiy menyu")
async def main_menu(message: Message):
    await show_main_menu(message, message.from_user.id)
