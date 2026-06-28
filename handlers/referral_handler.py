"""
referral_handler.py — Referral tizimi handleri
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("referral"))
@router.message(F.text == "👥 Do'stlarni taklif qil")
async def show_referral(message: Message, bot: Bot):
    user_id = message.from_user.id

    if not await db.user_exists(user_id):
        await message.answer("❗ Avval ro'yxatdan o'ting.")
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username

    text = await db.get_referral_link_text(user_id, bot_username)
    await message.answer(text, parse_mode="HTML")


async def confirm_referral_after_registration(user_id: int, referrer_id: int, bot: Bot):
    """
    Bu funksiyani registration_handler.py dan chaqiring —
    yangi foydalanuvchi ro'yxatdan o'tib bo'lgandan keyin.
    """
    premium_given = await db.process_referral(user_id, referrer_id)
    stats = await db.get_referral_stats(referrer_id)

    if premium_given:
        try:
            await bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Siz {stats['ref_count']} ta do'stingizni taklif qildingiz!\n"
                    f"🎁 Sizga <b>1 kunlik bepul premium</b> berildi!\n\n"
                    f"Premium imkoniyatlardan bahramand bo'ling 🌟"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Referrer {referrer_id} ga xabar yuborib bo'lmadi: {e}")
    else:
        try:
            await bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"👥 <b>Yangi do'stingiz qo'shildi!</b>\n\n"
                    f"Jami taklif qilganlar: <b>{stats['ref_count']}</b> ta\n"
                    f"Keyingi bepul premiumgacha: <b>{stats['next_premium_in']}</b> ta do'st\n\n"
                    f"Davom eting! 💪"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Referrer {referrer_id} ga xabar yuborib bo'lmadi: {e}")
