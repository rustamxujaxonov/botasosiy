import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from database import (
    get_chat_partner, end_chat, is_in_chat,
    is_in_queue, remove_from_queue, is_premium,
    get_user
)
from keyboards import kb_in_chat, kb_main_menu
from handlers.search_handler import start_search

logger = logging.getLogger(__name__)
router = Router()

# Qo'llab-quvvatlanadigan xabar turlari
SUPPORTED_CONTENT_TYPES = {
    "text", "photo", "video", "voice", "audio",
    "document", "sticker", "animation", "video_note"
}


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
        reply_markup=kb_main_menu(is_premium_user=premium_self),
        parse_mode="HTML"
    )

    if partner_id:
        try:
            premium_partner = await is_premium(partner_id)
            await message.bot.send_message(
                chat_id=partner_id,
                text="🚫 <b>Muloqotchi chatdan chiqdi.</b>\n\n"
                     "Yangi muloqotchi qidirish uchun tugmani bosing.",
                reply_markup=kb_main_menu(is_premium_user=premium_partner),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Partner disconnect xabari yuborishda xato: {e}")


@router.message(F.text == "⏭ Keyingisi")
async def next_partner(message: Message):
    user_id = message.from_user.id

    # Eski chatdan chiqish
    partner_id = await get_chat_partner(user_id)
    if partner_id:
        await end_chat(user_id)
        try:
            premium_partner = await is_premium(partner_id)
            await message.bot.send_message(
                chat_id=partner_id,
                text="⏭ <b>Muloqotchi yangi suhbatdosh qidirmoqda.</b>\n\n"
                     "Siz ham yangi muloqotchi topishingiz mumkin!",
                reply_markup=kb_main_menu(is_premium_user=premium_partner),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Partner skip xabari yuborishda xato: {e}")

    # Yangi qidirish
    await start_search(message, "any")


async def relay_message(message: Message, partner_id: int):
    """Xabarni sherikka uzatish"""
    bot = message.bot

    try:
        if message.text:
            await bot.send_message(
                chat_id=partner_id,
                text=message.text
            )

        elif message.photo:
            await bot.send_photo(
                chat_id=partner_id,
                photo=message.photo[-1].file_id,
                caption=message.caption or None
            )

        elif message.video:
            await bot.send_video(
                chat_id=partner_id,
                video=message.video.file_id,
                caption=message.caption or None
            )

        elif message.voice:
            await bot.send_voice(
                chat_id=partner_id,
                voice=message.voice.file_id
            )

        elif message.audio:
            await bot.send_audio(
                chat_id=partner_id,
                audio=message.audio.file_id,
                caption=message.caption or None
            )

        elif message.document:
            await bot.send_document(
                chat_id=partner_id,
                document=message.document.file_id,
                caption=message.caption or None
            )

        elif message.sticker:
            await bot.send_sticker(
                chat_id=partner_id,
                sticker=message.sticker.file_id
            )

        elif message.animation:
            await bot.send_animation(
                chat_id=partner_id,
                animation=message.animation.file_id,
                caption=message.caption or None
            )

        elif message.video_note:
            await bot.send_video_note(
                chat_id=partner_id,
                video_note=message.video_note.file_id
            )

        else:
            await message.answer("⚠️ Bu turdagi xabar uzatilmaydi.")

    except Exception as e:
        logger.error(f"Xabar uzatishda xato: {e}")


@router.message(
    F.content_type.in_(SUPPORTED_CONTENT_TYPES),
    ~F.text.startswith("/"),
    ~F.text.in_({
        "🔍 Muloqotchi qidirish",
        "👧 Qiz qidirish", "👧 Qiz qidirish ⭐",
        "👦 Yigit qidirish", "👦 Yigit qidirish ⭐",
        "👤 Profil sozlamalari",
        "🏠 Asosiy menyu",
        "🚫 Chatdan chiqish",
        "⏭ Keyingisi",
        "❌ Qidirishni to'xtatish",
    })
)
async def handle_message_in_chat(message: Message):
    user_id = message.from_user.id

    # Chatda bo'lsa, uzatish
    if await is_in_chat(user_id):
        partner_id = await get_chat_partner(user_id)
        if partner_id:
            await relay_message(message, partner_id)
        else:
            # Chat record bor, lekin partner yo'q
            await end_chat(user_id)
            premium = await is_premium(user_id)
            await message.answer(
                "❌ Muloqotchi topa olmadi. Asosiy menyuga qaytdingiz.",
                reply_markup=kb_main_menu(is_premium_user=premium)
            )
        return

    # Navbatda bo'lsa
    if await is_in_queue(user_id):
        await message.answer("⏳ Muloqotchi qidirilmoqda, biroz kuting...")
        return

    # Hech qayerda bo'lmasa - menyuga yo'naltirish
    premium = await is_premium(user_id)
    await message.answer(
        "💬 Muloqot boshlash uchun «🔍 Muloqotchi qidirish» tugmasini bosing.",
        reply_markup=kb_main_menu(is_premium_user=premium)
    )
