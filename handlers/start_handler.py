"""
start_handler.py
Tuzatishlar:
- proceed_after_subscription'da message/bot to'g'ri uzatiladi
- callback'dan kelganda message.chat.id ishlatiladi
"""

import logging
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from config import CHANNEL_ID
from database import create_or_update_user, user_exists
from keyboards import kb_check_subscription

logger = logging.getLogger(__name__)
router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi kanalga obuna bo'lganini tekshirish"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception as e:
        logger.error(f"Obuna tekshirishda xato: {e}")
        # Xato bo'lsa — o'tkazib yuboramiz (bot kanalda admin emas bo'lishi mumkin)
        return True


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    await create_or_update_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

    is_subscribed = await check_subscription(bot, user.id)

    if not is_subscribed:
        await message.answer(
            "👋 <b>Xush kelibsiz!</b>\n\n"
            "🔐 Botdan foydalanish uchun avval bizning kanalga obuna bo'lishingiz kerak.\n\n"
            "📢 Obuna bo'lgach, <b>«✅ Obunani tekshirish»</b> tugmasini bosing."
        )
        await message.answer(
            "👇 Obuna bo'lish uchun:",
            reply_markup=kb_check_subscription()
        )
        return

    await _after_subscription(bot, message.chat.id, user.id)


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    is_subscribed = await check_subscription(bot, callback.from_user.id)

    if not is_subscribed:
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz!",
            show_alert=True
        )
        return

    # Tugma xabarini o'chirish
    try:
        await callback.message.delete()
    except Exception:
        pass

    await _after_subscription(bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


async def _after_subscription(bot: Bot, chat_id: int, user_id: int):
    """Obuna tasdiqlanganidan keyin keyingi qadam"""
    is_registered = await user_exists(user_id)

    if is_registered:
        from handlers.menu_handler import send_main_menu
        await send_main_menu(bot, chat_id, user_id)
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "📋 <b>Ro'yxatdan o'tish</b>\n\n"
                "Bu ma'lumotlar anonim saqlanadi va boshqalarga ko'rsatilmaydi.\n\n"
                "👤 Avval jinsingizni tanlang:"
            ),
            reply_markup=__import__('keyboards').kb_gender()
        )
