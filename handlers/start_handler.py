"""
start_handler.py — /start komandasi + referral havolalarni qayta ishlash

Yangilik: /start ref_12345678 → referral tizimi ishga tushadi
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import start_keyboard, main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot=None):
    user_id   = message.from_user.id
    username  = message.from_user.username
    full_name = message.from_user.full_name

    # Referral parametrini tekshirish: /start ref_12345678
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
            if referrer_id == user_id:
                referrer_id = None  # O'zini chaqira olmaydi
        except (ValueError, IndexError):
            referrer_id = None

    # Foydalanuvchini yaratish/yangilash
    await db.create_or_update_user(
        user_id=user_id,
        username=username,
        full_name=full_name,
        referrer_id=referrer_id
    )

    # Ro'yxatdan o'tganmi?
    if await db.user_exists(user_id):
        await message.answer(
            f"👋 <b>Xush kelibsiz, {full_name}!</b>\n\n"
            f"Nima qilmoqchisiz?",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    # Yangi foydalanuvchi
    ref_text = ""
    if referrer_id:
        ref_text = f"\n\n🎁 <i>Siz do'stingiz taklifi bilan keldingiz!</i>"

    await message.answer(
        f"👋 <b>Salom, {full_name}!</b>\n\n"
        f"Bu anonim tanishuv botiga xush kelibsiz!{ref_text}\n\n"
        f"Boshlash uchun ro'yxatdan o'ting 👇",
        reply_markup=start_keyboard(),
        parse_mode="HTML"
    )

    # Referral qayta ishlash (ro'yxatdan o'tgandan keyin bo'ladi,
    # shuning uchun bu yerda faqat saqlaymiz — complete_registration dan keyin chaqiriladi)
    if referrer_id:
        await state.update_data(pending_referrer_id=referrer_id)
