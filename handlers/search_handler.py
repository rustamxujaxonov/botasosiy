"""
search_handler.py
Tuzatishlar:
- find_match endi database ichida transaction bilan ishlaydi (race condition yo'q)
- create_chat chaqiruvi olib tashlandi (find_match o'zi yaratadi)
- asyncio.create_task xavfsiz ishlatiladi
- None text crash'i yo'q
"""

import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message

from database import (
    get_user, is_premium,
    add_to_queue, remove_from_queue, find_match,
    is_in_queue, is_in_chat, get_chat_partner, end_chat
)
from keyboards import kb_in_chat, kb_stop_search, kb_main_menu

logger = logging.getLogger(__name__)
router = Router()


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
        await message.answer("❗ Avval ro'yxatdan o'ting. /start bosing.")
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

    my_gender = user.get("gender", "male")

    # Avval birini topishga urinish (navbatga qo'shishdan oldin)
    partner_id = await find_match(user_id, my_gender, search_type)

    if partner_id:
        # Darhol uchrashuv
        await _connect_users(message.bot, user_id, partner_id)
    else:
        # Navbatga qo'shish
        await add_to_queue(user_id, my_gender, search_type)

        label = {"any": "🔍 Muloqotchi", "female": "👧 Qiz", "male": "👦 Yigit"}.get(search_type, "🔍 Muloqotchi")

        await message.answer(
            f"⏳ <b>{label} qidirilmoqda...</b>\n\n"
            f"Mos muloqotchi topilishi bilan ulanasiz.\n"
            f"Bekor qilish uchun tugmani bosing.",
            reply_markup=kb_stop_search()
        )

        # Fon rejimda kutish
        asyncio.create_task(
            _wait_for_match(message, user_id, my_gender, search_type)
        )


async def _wait_for_match(
    message: Message, user_id: int, my_gender: str,
    search_type: str, timeout: int = 120
):
    """Fon rejimda mos foydalanuvchi kutish"""
    waited   = 0
    interval = 4  # har 4 soniyada tekshirish

    while waited < timeout:
        await asyncio.sleep(interval)
        waited += interval

        # Hali navbatdami?
        if not await is_in_queue(user_id):
            return  # Bekor qilindi yoki allaqachon ulanildi

        # Mos topilganmi? (find_match navbatdan ham olib tashlaydi)
        partner_id = await find_match(user_id, my_gender, search_type)
        if partner_id:
            await _connect_users(message.bot, user_id, partner_id)
            return

    # Timeout — navbatdan chiqarish
    if await is_in_queue(user_id):
        await remove_from_queue(user_id)
        try:
            premium = await is_premium(user_id)
            await message.bot.send_message(
                chat_id=user_id,
                text=(
                    "😔 <b>Muloqotchi topilmadi.</b>\n\n"
                    "Hozircha qidirayotgan foydalanuvchi yo'q.\n"
                    "Keyinroq qayta urinib ko'ring!"
                ),
                reply_markup=kb_main_menu(is_premium_user=premium)
            )
        except Exception as e:
            logger.error(f"Timeout xabar yuborishda xato: {e}")


async def _connect_users(bot, user1_id: int, user2_id: int):
    """
    Ikki foydalanuvchiga ulanish xabarini yuborish.
    Chat allaqachon find_match ichida yaratilgan.
    """
    try:
        user1 = await get_user(user1_id)
        user2 = await get_user(user2_id)
        prem1 = await is_premium(user1_id)
        prem2 = await is_premium(user2_id)

        await bot.send_message(
            chat_id=user1_id,
            text=(
                "✅ <b>Muloqotchi topildi!</b>\n\n"
                f"{_partner_info(user2, prem1)}\n\n"
                "💬 Yozing, muloqot boshlandi!\n\n"
                "⏭ «Keyingisi» — yangi muloqotchi\n"
                "🚫 «Chatdan chiqish» — menyuga qaytish"
            ),
            reply_markup=kb_in_chat()
        )

        await bot.send_message(
            chat_id=user2_id,
            text=(
                "✅ <b>Muloqotchi topildi!</b>\n\n"
                f"{_partner_info(user1, prem2)}\n\n"
                "💬 Yozing, muloqot boshlandi!\n\n"
                "⏭ «Keyingisi» — yangi muloqotchi\n"
                "🚫 «Chatdan chiqish» — menyuga qaytish"
            ),
            reply_markup=kb_in_chat()
        )

    except Exception as e:
        logger.error(f"Foydalanuvchilarni ulashda xato: {e}")
        # Xato bo'lsa chatni yopish
        await end_chat(user1_id)


def _partner_info(partner: dict, viewer_is_premium: bool) -> str:
    if viewer_is_premium:
        g = "👧" if partner.get("gender") == "female" else "👦"
        return (
            f"👤 Muloqotchi:\n"
            f"{g} Taxallus: <b>{partner.get('display_name', '—')}</b>\n"
            f"🔢 Yosh: <b>{partner.get('age', '—')}</b>\n"
            f"📍 Viloyat: <b>{partner.get('region', '—')}</b>"
        )
    return "👤 Muloqotchi: <b>Anonim</b>"


# ============================================================
# BUTTON HANDLERS
# ============================================================

@router.message(F.text == "🔍 Muloqotchi qidirish")
async def free_search(message: Message):
    await start_search(message, "any")


@router.message(F.text.in_({"👧 Qiz qidirish", "👧 Qiz qidirish ⭐"}))
async def search_girl(message: Message):
    if not await is_premium(message.from_user.id):
        from handlers.premium_handler import show_premium_info
        await show_premium_info(message)
        return
    await start_search(message, "female")


@router.message(F.text.in_({"👦 Yigit qidirish", "👦 Yigit qidirish ⭐"}))
async def search_boy(message: Message):
    if not await is_premium(message.from_user.id):
        from handlers.premium_handler import show_premium_info
        await show_premium_info(message)
        return
    await start_search(message, "male")


@router.message(F.text == "❌ Qidirishni to'xtatish")
async def cancel_search(message: Message):
    user_id = message.from_user.id
    premium = await is_premium(user_id)

    if await is_in_queue(user_id):
        await remove_from_queue(user_id)
        await message.answer(
            "❌ Qidirish to'xtatildi.",
            reply_markup=kb_main_menu(is_premium_user=premium)
        )
    else:
        await message.answer(
            "ℹ️ Siz qidirish navbatida emassiz.",
            reply_markup=kb_main_menu(is_premium_user=premium)
        )
