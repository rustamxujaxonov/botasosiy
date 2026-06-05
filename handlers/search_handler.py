import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message

from database import (
    get_user, is_premium,
    add_to_queue, remove_from_queue, find_match,
    is_in_queue, is_in_chat,
    create_chat, get_chat_partner, end_chat
)
from keyboards import kb_in_chat, kb_stop_search, kb_main_menu

logger = logging.getLogger(__name__)
router = Router()

# Qidirish kutayotgan foydalanuvchilarni kuzatish uchun
_pending_searches: dict = {}


async def start_search(message: Message, search_type: str = "any"):
    """
    search_type:
      'any'    - tekin, istalgan jins
      'female' - premium, qizlar
      'male'   - premium, yigitlar
    """
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("registered"):
        await message.answer("❗ Avval ro'yxatdan o'ting. /start")
        return

    # Agar allaqachon chatda bo'lsa
    if await is_in_chat(user_id):
        await message.answer(
            "⚠️ Siz allaqachon muloqotda ekansiz!\n"
            "Chatdan chiqish uchun «🚫 Chatdan chiqish» tugmasini bosing.",
            reply_markup=kb_in_chat()
        )
        return

    # Agar allaqachon navbatda bo'lsa
    if await is_in_queue(user_id):
        await message.answer("⏳ Siz allaqachon qidirish navbatidasiz...")
        return

    user_gender = user.get("gender", "male")

    # Navbatga qo'shish
    await add_to_queue(user_id, user_gender, search_type)

    search_label = {
        "any": "🔍 Muloqotchi",
        "female": "👧 Qiz",
        "male": "👦 Yigit"
    }.get(search_type, "🔍 Muloqotchi")

    await message.answer(
        f"⏳ <b>{search_label} qidirilmoqda...</b>\n\n"
        f"Mos muloqotchi topilishi bilan ulanasiz.\n"
        f"Bekor qilish uchun tugmani bosing.",
        reply_markup=kb_stop_search(),
        parse_mode="HTML"
    )

    # Mos foydalanuvchini qidirish
    partner_id = await find_match(user_id, user_gender, search_type)

    if partner_id:
        await connect_users(message, user_id, partner_id, search_type)
    else:
        # Fon rejimda kutish
        asyncio.create_task(wait_for_match(message, user_id, user_gender, search_type))


async def wait_for_match(message: Message, user_id: int, user_gender: str, search_type: str,
                          timeout: int = 120):
    """Mos foydalanuvchi topilguncha kutish"""
    waited = 0
    interval = 3

    while waited < timeout:
        await asyncio.sleep(interval)
        waited += interval

        # Hali navbatdami?
        if not await is_in_queue(user_id):
            return  # Bekor qilindi yoki ulanildi

        partner_id = await find_match(user_id, user_gender, search_type)
        if partner_id:
            await connect_users(message, user_id, partner_id, search_type)
            return

    # Timeout
    if await is_in_queue(user_id):
        await remove_from_queue(user_id)
        try:
            premium = await is_premium(user_id)
            await message.answer(
                "😔 <b>Muloqotchi topilmadi.</b>\n\n"
                "Hozircha qidirayotgan foydalanuvchi yo'q.\n"
                "Keyinroq qayta urinib ko'ring!",
                reply_markup=kb_main_menu(is_premium_user=premium),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Timeout xabar yuborishda xato: {e}")


async def connect_users(message: Message, user1_id: int, user2_id: int, search_type: str):
    """Ikki foydalanuvchini ulash"""
    try:
        # Navbatdan olib tashlash
        await remove_from_queue(user1_id)
        await remove_from_queue(user2_id)

        # Chat yaratish
        await create_chat(user1_id, user2_id)

        user2 = await get_user(user2_id)
        user1 = await get_user(user1_id)

        premium1 = await is_premium(user1_id)
        premium2 = await is_premium(user2_id)

        # User1 uchun xabar
        partner_info_1 = build_partner_info(user2, premium1)
        await message.bot.send_message(
            chat_id=user1_id,
            text=(
                "✅ <b>Muloqotchi topildi!</b>\n\n"
                f"{partner_info_1}\n"
                "💬 Yozing, muloqot boshlandi!\n\n"
                "⏭ «Keyingisi» — yangi muloqotchi\n"
                "🚫 «Chatdan chiqish» — menyuga qaytish"
            ),
            reply_markup=kb_in_chat(),
            parse_mode="HTML"
        )

        # User2 uchun xabar
        partner_info_2 = build_partner_info(user1, premium2)
        await message.bot.send_message(
            chat_id=user2_id,
            text=(
                "✅ <b>Muloqotchi topildi!</b>\n\n"
                f"{partner_info_2}\n"
                "💬 Yozing, muloqot boshlandi!\n\n"
                "⏭ «Keyingisi» — yangi muloqotchi\n"
                "🚫 «Chatdan chiqish» — menyuga qaytish"
            ),
            reply_markup=kb_in_chat(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Foydalanuvchilarni ulashda xato: {e}")
        await end_chat(user1_id)


def build_partner_info(partner: dict, viewer_is_premium: bool) -> str:
    """Premium bo'lsa to'liq ma'lumot, aks holda anonim"""
    if viewer_is_premium:
        gender_emoji = "👧" if partner.get("gender") == "female" else "👦"
        return (
            f"👤 Muloqotchi ma'lumotlari:\n"
            f"{gender_emoji} Taxallus: <b>{partner.get('display_name', '—')}</b>\n"
            f"🔢 Yosh: <b>{partner.get('age', '—')}</b>\n"
            f"📍 Viloyat: <b>{partner.get('region', '—')}</b>"
        )
    else:
        return "👤 Muloqotchi: <b>Anonim</b>"


# ============================================================
# BUTTON HANDLERS
# ============================================================

@router.message(F.text == "🔍 Muloqotchi qidirish")
async def free_search(message: Message):
    premium = await is_premium(message.from_user.id)
    await start_search(message, "any")


@router.message(F.text.in_({"👧 Qiz qidirish", "👧 Qiz qidirish ⭐"}))
async def search_girl(message: Message):
    premium = await is_premium(message.from_user.id)
    if not premium:
        from handlers.premium_handler import show_premium_info
        await show_premium_info(message)
        return
    await start_search(message, "female")


@router.message(F.text.in_({"👦 Yigit qidirish", "👦 Yigit qidirish ⭐"}))
async def search_boy(message: Message):
    premium = await is_premium(message.from_user.id)
    if not premium:
        from handlers.premium_handler import show_premium_info
        await show_premium_info(message)
        return
    await start_search(message, "male")


@router.message(F.text == "❌ Qidirishni to'xtatish")
async def cancel_search(message: Message):
    user_id = message.from_user.id

    if await is_in_queue(user_id):
        await remove_from_queue(user_id)
        premium = await is_premium(user_id)
        await message.answer(
            "❌ Qidirish to'xtatildi.",
            reply_markup=kb_main_menu(is_premium_user=premium)
        )
    else:
        premium = await is_premium(user_id)
        await message.answer(
            "ℹ️ Siz qidirish navbatida emassiz.",
            reply_markup=kb_main_menu(is_premium_user=premium)
        )
