"""
chat_handler.py
Tuzatishlar:
- F.text None bo'lganda crash yo'q (photo, sticker va h.k. uchun)
- Filter to'g'ri yozildi: text bo'lmagan media ham relay qilinadi
- copy_to ishlatildi — barcha media turlarini bir joyda hal qiladi
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from database import (
    get_chat_partner, end_chat, is_in_chat,
    is_in_queue, remove_from_queue, is_premium
)
from keyboards import kb_in_chat, kb_main_menu
from handlers.search_handler import start_search

logger = logging.getLogger(__name__)
router = Router()

# Menyudagi tugma matnlari (bu xabarlar relay qilinmaydi)
_MENU_TEXTS = {
    "🔍 Muloqotchi qidirish",
    "👧 Qiz qidirish",
    "👧 Qiz qidirish ⭐",
    "👦 Yigit qidirish",
    "👦 Yigit qidirish ⭐",
    "👤 Profil sozlamalari",
    "🏠 Asosiy menyu",
    "🚫 Chatdan chiqish",
    "⏭ Keyingisi",
    "❌ Qidirishni to'xtatish",
}


# ============================================================
# CHATDAN CHIQISH
# ============================================================

@router.message(F.text == "🚫 Chatdan chiqish")
async def leave_chat(message: Message):
    user_id = message.from_user.id

    if not await is_in_chat(user_id):
        premium = await is_premium(user_id)
        await message.answer(
            "ℹ️ Siz hozir hech kimga ulanmagan ekansiz.",
            reply_markup=kb_main_menu(is_premium_user=premium)
        )
        return

    partner_id = await get_chat_partner(user_id)
    await end_chat(user_id)

    premium_self = await is_premium(user_id)
    await message.answer(
        "🚫 <b>Muloqot yakunlandi.</b>\n\n"
        "Yangi muloqotchi topish uchun tugmani bosing.",
        reply_markup=kb_main_menu(is_premium_user=premium_self)
    )

    if partner_id:
        try:
            premium_partner = await is_premium(partner_id)
            await message.bot.send_message(
                chat_id=partner_id,
                text=(
                    "🚫 <b>Muloqotchi chatdan chiqdi.</b>\n\n"
                    "Yangi muloqotchi qidirish uchun tugmani bosing."
                ),
                reply_markup=kb_main_menu(is_premium_user=premium_partner)
            )
        except Exception as e:
            logger.error(f"Partner disconnect xabari yuborishda xato: {e}")


# ============================================================
# KEYINGISI
# ============================================================

@router.message(F.text == "⏭ Keyingisi")
async def next_partner(message: Message):
    user_id = message.from_user.id

    partner_id = await get_chat_partner(user_id)
    if partner_id:
        await end_chat(user_id)
        try:
            premium_partner = await is_premium(partner_id)
            await message.bot.send_message(
                chat_id=partner_id,
                text=(
                    "⏭ <b>Muloqotchi yangi suhbatdosh qidirmoqda.</b>\n\n"
                    "Siz ham yangi muloqotchi topishingiz mumkin!"
                ),
                reply_markup=kb_main_menu(is_premium_user=premium_partner)
            )
        except Exception as e:
            logger.error(f"Partner skip xabari yuborishda xato: {e}")

    await start_search(message, "any")


# ============================================================
# XABAR RELAY (barcha media turlari)
# ============================================================

async def _relay(message: Message, partner_id: int):
    """
    copy_to — eng ishonchli usul: caption, media_group, parse_mode
    hamma narsa avtomatik saqlanadi.
    """
    try:
        await message.copy_to(chat_id=partner_id)
    except Exception as e:
        logger.error(f"Xabar copy_to da xato: {e}")
        # Fallback: manual relay
        await _relay_manual(message, partner_id)


async def _relay_manual(message: Message, partner_id: int):
    """copy_to ishlamasa — manual relay"""
    bot: Bot = message.bot
    try:
        if message.text:
            await bot.send_message(partner_id, message.text)
        elif message.photo:
            await bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            await bot.send_video(partner_id, message.video.file_id, caption=message.caption)
        elif message.voice:
            await bot.send_voice(partner_id, message.voice.file_id)
        elif message.audio:
            await bot.send_audio(partner_id, message.audio.file_id, caption=message.caption)
        elif message.document:
            await bot.send_document(partner_id, message.document.file_id, caption=message.caption)
        elif message.sticker:
            await bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.animation:
            await bot.send_animation(partner_id, message.animation.file_id, caption=message.caption)
        elif message.video_note:
            await bot.send_video_note(partner_id, message.video_note.file_id)
        elif message.location:
            await bot.send_location(partner_id, message.location.latitude, message.location.longitude)
        else:
            await message.answer("⚠️ Bu turdagi xabar uzatilmaydi.")
    except Exception as e:
        logger.error(f"Manual relay da xato: {e}")


@router.message()
async def handle_any_message(message: Message):
    """
    Barcha xabarlarni ushlaydigan universal handler.
    Bu handler oxirida turadigan router'ga yoziladi.
    """
    user_id = message.from_user.id

    # Menyudagi tugmalarni o'tkazib yuborish
    if message.text and message.text in _MENU_TEXTS:
        return

    # Komandalarni o'tkazib yuborish
    if message.text and message.text.startswith("/"):
        return

    # CHATDA BO'LSA → relay
    if await is_in_chat(user_id):
        partner_id = await get_chat_partner(user_id)
        if partner_id:
            await _relay(message, partner_id)
        else:
            await end_chat(user_id)
            premium = await is_premium(user_id)
            await message.answer(
                "❌ Muloqotchi topa olmadi. Asosiy menyuga qaytdingiz.",
                reply_markup=kb_main_menu(is_premium_user=premium)
            )
        return

    # NAVBATDA BO'LSA
    if await is_in_queue(user_id):
        await message.answer("⏳ Muloqotchi qidirilmoqda, biroz kuting...")
        return

    # HECH QAYERDA BO'LMASA
    premium = await is_premium(user_id)
    await message.answer(
        "💬 Muloqot boshlash uchun «🔍 Muloqotchi qidirish» tugmasini bosing.",
        reply_markup=kb_main_menu(is_premium_user=premium)
    )
