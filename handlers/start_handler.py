"""
start_handler.py — /start komandasi + referral havolalarni qayta ishlash
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import kb_check_subscription, kb_main_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    user_id   = message.from_user.id
    username  = message.from_user.username
    full_name = message.from_user.full_name

    # Referral parametrini tekshirish: /start ref_12345678
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
            if referrer_id == user_id:
                referrer_id = None
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
        is_prem = await db.is_premium(user_id)
        await message.answer(
            f"👋 <b>Xush kelibsiz, {full_name}!</b>\n\nNima qilmoqchisiz?",
            reply_markup=kb_main_menu(is_premium_user=is_prem),
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
        f"Boshlash uchun avval kanalimizga obuna bo'ling 👇",
        reply_markup=kb_check_subscription(),
        parse_mode="HTML"
    )

    # Referral'ni state'ga saqlash (ro'yxatdan o'tgandan keyin ishlatiladi)
    if referrer_id:
        await state.update_data(pending_referrer_id=referrer_id)
