"""
referral_handler.py — Referral tizimi handleri

Funksiyalar:
- Foydalanuvchi o'z referral havolasini oladi
- Statistikani ko'radi (nechta do'st, qachon premium)
- Ro'yxatdan o'tgan yangi foydalanuvchi referral'ni tasdiqlaydi
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db

logger = logging.getLogger(__name__)
router = Router()


# ============================================================
# REFERRAL HAVOLANI OLISH
# ============================================================

@router.message(Command("referral"))
@router.message(F.text == "👥 Do'stlarni taklif qil")
@router.callback_query(F.data == "show_referral")
async def show_referral(event: Message | CallbackQuery, bot: Bot):
    """Foydalanuvchiga uning referral havolasini ko'rsatish"""

    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        send = event.message.answer
        await event.answer()
    else:
        user_id = event.from_user.id
        send = event.answer

    # Bot username'ni olish
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    # Ro'yxatdan o'tganligini tekshirish
    if not await db.user_exists(user_id):
        await send("❗ Avval ro'yxatdan o'ting.")
        return

    text = await db.get_referral_link_text(user_id, bot_username)
    await send(text, parse_mode="HTML")


# ============================================================
# RO'YXATDAN O'TGANDAN KEYIN REFERRAL TASDIQLASH
# ============================================================

async def confirm_referral_after_registration(user_id: int, referrer_id: int, bot: Bot):
    """
    Bu funksiya registration_handler.py dan chaqiriladi —
    yangi foydalanuvchi ro'yxatdan o'tib bo'lgandan keyin.
    
    Args:
        user_id:     Yangi foydalanuvchi ID
        referrer_id: Taklif qilgan foydalanuvchi ID
        bot:         Bot obyekti (referrer'ga xabar yuborish uchun)
    """
    premium_given = await db.process_referral(user_id, referrer_id)

    if premium_given:
        # Referrer'ga xabar yuborish
        stats = await db.get_referral_stats(referrer_id)
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
        # Odatdagi bildirishnoma
        stats = await db.get_referral_stats(referrer_id)
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
