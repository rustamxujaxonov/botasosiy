"""
search_handler.py — Yaxshilangan qidiruv tizimi

Muammo (oldin):
  - Vaqt tugasa "topilmadi, keyinroq urinib ko'ring" deb TO'XTATIB qo'yardi

Yechim (endi):
  - Har 30 sekundda "hali qidiryapman..." xabari chiqaradi
  - Foydalanuvchi o'zi to'xtatgunicha qidiraveradi
  - Navbatdagi odamlar sonini ko'rsatadi
  - "Bekor qilish" tugmasi har doim ko'rinadi
"""

import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import search_keyboard, main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Qidiruv intervallari (sekundda)
CHECK_INTERVAL   = 5    # Har 5 sekundda match qidiriladi
STATUS_INTERVAL  = 30   # Har 30 sekundda foydalanuvchiga xabar
MAX_WAIT_MINUTES = 30   # Maksimum kutish (so'ngra qayta so'rash)

class SearchState(StatesGroup):
    searching = State()

# ============================================================
# QIDIRUV BOSHLASH
# ============================================================

@router.callback_query(F.data == "search_any")
async def start_search_any(callback: CallbackQuery, state: FSMContext):
    await _start_search(callback.message, callback.from_user.id, state, "any")
    await callback.answer()

@router.callback_query(F.data == "search_male")
async def start_search_male(callback: CallbackQuery, state: FSMContext):
    await _start_search(callback.message, callback.from_user.id, state, "male")
    await callback.answer()

@router.callback_query(F.data == "search_female")
async def start_search_female(callback: CallbackQuery, state: FSMContext):
    await _start_search(callback.message, callback.from_user.id, state, "female")
    await callback.answer()

async def _start_search(message: Message, user_id: int, state: FSMContext, search_type: str):
    """Qidiruvni boshlash"""
    # Avval boshqa chatda yoki navbatda emasligini tekshirish
    if await db.is_in_chat(user_id):
        await message.answer("❗ Siz hozir chat ichida ekansiz. Avval chatni yakunlang.")
        return

    user = await db.get_user(user_id)
    if not user or not user["registered"]:
        await message.answer("❗ Avval ro'yxatdan o'ting.")
        return

    my_gender = user["gender"]
    await db.add_to_queue(user_id, my_gender, search_type)
    await state.set_state(SearchState.searching)
    await state.update_data(search_type=search_type, my_gender=my_gender, waited=0)

    search_type_text = {
        "any":    "istalgan",
        "male":   "erkak",
        "female": "ayol"
    }.get(search_type, "istalgan")

    queue_size = await db.get_queue_size()

    msg = await message.answer(
        f"🔍 <b>Muloqotchi qidirilmoqda...</b>\n\n"
        f"Qidiruv turi: <b>{search_type_text}</b>\n"
        f"Navbatda: <b>{queue_size}</b> ta foydalanuvchi\n\n"
        f"⏳ Muloqotchi topilguncha kuting...\n"
        f"(O'zingiz bekor qilmasangiz qidiraveradi)",
        reply_markup=search_keyboard()
    )

    # Fon vazifasi sifatida qidiruvni ishga tushirish
    asyncio.create_task(
        _search_loop(message, user_id, my_gender, search_type, state, msg.message_id)
    )

# ============================================================
# QIDIRUV LOOPI
# ============================================================

async def _search_loop(
    message: Message,
    user_id: int,
    my_gender: str,
    search_type: str,
    state: FSMContext,
    status_msg_id: int
):
    """
    Foydalanuvchi bekor qilmaguncha yoki match topilmaguncha ishlaydi.
    To'xtatmaydi — faqat foydalanuvchi o'zi bekor qiladi.
    """
    elapsed = 0
    status_elapsed = 0
    bot = message.bot

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        elapsed        += CHECK_INTERVAL
        status_elapsed += CHECK_INTERVAL

        # FSM holatini tekshirish (bekor qilinganmi?)
        current_state = await state.get_state()
        if current_state != SearchState.searching:
            logger.info(f"User {user_id}: qidiruv bekor qilindi (state o'zgardi)")
            return

        # Navbatda hali turganligini tekshirish
        if not await db.is_in_queue(user_id):
            logger.info(f"User {user_id}: navbatdan chiqib ketdi (match topilgan bo'lishi mumkin)")
            # Match topilgan — chat_handler uni ushlab oladi
            return

        # Match qidirish
        partner_id = await db.find_match(user_id, my_gender, search_type)

        if partner_id:
            # ✅ MATCH TOPILDI
            await state.clear()
            await _on_match_found(bot, user_id, partner_id, message.chat.id, status_msg_id)
            return

        # Har STATUS_INTERVAL sekundda xabar yangilash
        if status_elapsed >= STATUS_INTERVAL:
            status_elapsed = 0
            minutes = elapsed // 60
            seconds = elapsed % 60

            queue_size = await db.get_queue_size()
            wait_text = f"{minutes} daq {seconds} son" if minutes > 0 else f"{seconds} son"

            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg_id,
                    text=(
                        f"🔍 <b>Muloqotchi qidirilmoqda...</b>\n\n"
                        f"⏱ Kutish vaqti: <b>{wait_text}</b>\n"
                        f"👥 Navbatda: <b>{queue_size}</b> ta foydalanuvchi\n\n"
                        f"🔄 Qidiruv davom etmoqda...\n"
                        f"Bekor qilish uchun quyidagi tugmani bosing."
                    ),
                    reply_markup=search_keyboard(),
                    parse_mode="HTML"
                )
            except Exception:
                pass  # Xabar o'chirilgan bo'lsa — davom etish

        # MAX_WAIT_MINUTES dan oshsa — foydalanuvchiga xabar berish (lekin TO'XTATMASLIK)
        if elapsed > 0 and elapsed % (MAX_WAIT_MINUTES * 60) == 0:
            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"⏰ <b>{MAX_WAIT_MINUTES} daqiqa bo'ldi, hali ham qidiryapman.</b>\n\n"
                        f"Navbatda juda kam odam bor. Qidiruv davom etmoqda...\n"
                        f"Bekor qilmoqchi bo'lsangiz tugmani bosing."
                    ),
                    reply_markup=search_keyboard(),
                    parse_mode="HTML"
                )
            except Exception:
                pass

# ============================================================
# MATCH TOPILGANDA
# ============================================================

async def _on_match_found(bot, user_id: int, partner_id: int,
                           user_chat_id: int, status_msg_id: int):
    """Ikki foydalanuvchiga match xabarini yuborish"""

    # Status xabarni yangilash
    try:
        await bot.edit_message_text(
            chat_id=user_chat_id,
            message_id=status_msg_id,
            text="✅ <b>Muloqotchi topildi!</b> Salom deng 👋",
            parse_mode="HTML"
        )
    except Exception:
        await bot.send_message(
            chat_id=user_chat_id,
            text="✅ <b>Muloqotchi topildi!</b> Salom deng 👋",
            parse_mode="HTML"
        )

    # Sherikka ham xabar yuborish
    try:
        await bot.send_message(
            chat_id=partner_id,
            text="✅ <b>Muloqotchi topildi!</b> Salom deng 👋",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Partner {partner_id} ga xabar yuborilmadi: {e}")

# ============================================================
# QIDIRUVNI BEKOR QILISH
# ============================================================

@router.callback_query(F.data == "cancel_search")
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    await state.clear()
    await db.remove_from_queue(user_id)

    await callback.message.edit_text(
        "❌ <b>Qidiruv bekor qilindi.</b>\n\nBoshqa vaqt urinib ko'rishingiz mumkin.",
        parse_mode="HTML"
    )
    await callback.answer("Qidiruv bekor qilindi")

    # Asosiy menyu
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )

# ============================================================
# XABAR ORQALI HAM BEKOR QILISH
# ============================================================

@router.message(SearchState.searching, F.text.in_(["❌ Bekor qilish", "/stop"]))
async def cancel_search_by_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await db.remove_from_queue(user_id)

    await message.answer(
        "❌ <b>Qidiruv bekor qilindi.</b>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
