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
        return False


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
            "📢 Obuna bo'lgach, <b>«✅ Obunani tekshirish»</b> tugmasini bosing.",
            reply_markup=kb_check_subscription(),
            parse_mode="HTML"
        )
        return

    await proceed_after_subscription(message, user.id)


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    is_subscribed = await check_subscription(bot, callback.from_user.id)

    if not is_subscribed:
        await callback.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz!",
            show_alert=True
        )
        return

    await callback.message.delete()
    await proceed_after_subscription(callback.message, callback.from_user.id)
    await callback.answer()


async def proceed_after_subscription(message: Message, user_id: int):
    """Obuna bo'lgandan keyin keyingi qadamga o'tish"""
    is_registered = await user_exists(user_id)

    if is_registered:
        from handlers.menu_handler import show_main_menu
        await show_main_menu(message, user_id)
    else:
        from handlers.registration_handler import start_registration
        await start_registration(message)
