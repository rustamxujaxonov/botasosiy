"""
search_handler.py — Yaxshilangan qidiruv tizimi

Muammo (oldin):
  - Vaqt tugasa "topilmadi, keyinroq urinib ko'ring" deb TO'XTATIB qo'yardi

Yechim (endi):
  - Foydalanuvchi o'zi to'xtatgunicha qidiraveradi
  - Har 30 sekundda status xabari yangilanadi
  - Navbatdagi odamlar sonini ko'rsatadi
"""

import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import kb_stop_search, kb_main_menu

logger = logging.getLogger(__name__)
router = Router()

CHECK_INTERVAL  = 5    # Har 5 sekundda match qidiriladi
STATUS_INTERVAL = 30   # Har 30 sekundda xabar yangilanadi
MAX_WAIT_NOTIFY = 30   # 30 daqiqada bir marta eslatma (lekin to'xtatilmaydi)


class SearchState(StatesGroup):
    searching = State()


# ============================================================
# QIDIRUV BOSHLASH (mavjud search handlerga mos)
# ============================================================

async def start_search(message: Message, state: FSMContext, search_type: str):
    """
    Bu funksiyani menu_handler yoki boshqa handlerdan chaqiring:
        await start_search(message, state, "any")   # istalgan
        await start_search(message, state, "male")  # erkak
        await start_search(message, state, "female")# ayol
    """
    user_id = message.from_user.id

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
    await state.update_data(search_type=search_type, my_gender=my_gender)

    search_type_text = {
        "any":    "istalgan",
        "male":   "erkak",
        "female": "ayol"
    }.get(search_type, "istalgan")

    queue_size = await db.get_queue_size()

    sent = await message.answer(
        f"🔍 <b>Muloqotchi qidirilmoqda...</b>\n\n"
        f"Qidiruv turi: <b>{search_type_text}</b>\n"
        f"Navbatda: <b>{queue_size}</b> ta foydalanuvchi\n\n"
        f"⏳ Muloqotchi topilguncha kuting...\n"
        f"(O'zingiz to'xtatmasangiz qidiraveradi)",
        reply_markup=kb_stop_search(),
        parse_mode="HTML"
    )

    asyncio.create_task(
        _search_loop(message, user_id, my_gender, search_type, state, sent.message_id)
    )


# ============================================================
# QIDIRUV LOOPI — to'xtatmaydi, faqat foydalanuvchi bekor qiladi
# ============================================================

async def _search_loop(
    message: Message,
    user_id: int,
    my_gender: str,
    search_type: str,
    state: FSMContext,
    status_msg_id: int
):
    elapsed        = 0
    status_elapsed = 0
    bot            = message.bot

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        elapsed        += CHECK_INTERVAL
        status_elapsed += CHECK_INTERVAL

        # Bekor qilinganmi?
        current_state = await state.get_state()
        if current_state != SearchState.searching:
            return

        # Navbatdan chiqib ketganmi? (match topilgan)
        if not await db.is_in_queue(user_id):
            return

        # Match qidirish
        partner_id = await db.find_match(user_id, my_gender, search_type)
        if partner_id:
            await state.clear()
            await _on_match_found(bot, user_id, partner_id, message.chat.id, status_msg_id)
            return

        # Har STATUS_INTERVAL sekundda xabar yangilash
        if status_elapsed >= STATUS_INTERVAL:
            status_elapsed = 0
            minutes  = elapsed // 60
            seconds  = elapsed % 60
            wait_txt = f"{minutes} daq {seconds} son" if minutes > 0 else f"{seconds} son"
            queue_size = await db.get_queue_size()

            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_msg_id,
                    text=(
                        f"🔍 <b>Muloqotchi qidirilmoqda...</b>\n\n"
                        f"⏱ Kutish vaqti: <b>{wait_txt}</b>\n"
                        f"👥 Navbatda: <b>{queue_size}</b> ta foydalanuvchi\n\n"
                        f"🔄 Qidiruv davom etmoqda...\n"
                        f"To'xtatish uchun quyidagi tugmani bosing."
                    ),
                    reply_markup=kb_stop_search(),
                    parse_mode="HTML"
                )
            except Exception:
                pass

        # Har MAX_WAIT_NOTIFY daqiqada eslatma (lekin TO'XTATILMAYDI)
        if elapsed > 0 and elapsed % (MAX_WAIT_NOTIFY * 60) == 0:
            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"⏰ <b>{MAX_WAIT_NOTIFY} daqiqa bo'ldi, hali ham qidiryapman.</b>\n\n"
                        f"Navbatda kam odam bor, lekin qidiruv davom etmoqda...\n"
                        f"Bekor qilmoqchi bo'lsangiz tugmani bosing."
                    ),
                    reply_markup=kb_stop_search(),
                    parse_mode="HTML"
                )
            except Exception:
                pass


# ============================================================
# MATCH TOPILGANDA
# ============================================================

async def _on_match_found(bot, user_id: int, partner_id: int,
                           user_chat_id: int, status_msg_id: int):
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

    try:
        await bot.send_message(
            chat_id=partner_id,
            text="✅ <b>Muloqotchi topildi!</b> Salom deng 👋",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Partner {partner_id} ga xabar yuborib bo'lmadi: {e}")


# ============================================================
# QIDIRUVNI TO'XTATISH
# ============================================================

@router.message(SearchState.searching, F.text == "❌ Qidirishni to'xtatish")
async def cancel_search(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await db.remove_from_queue(user_id)

    is_prem = await db.is_premium(user_id)
    await message.answer(
        "❌ <b>Qidiruv to'xtatildi.</b>",
        reply_markup=kb_main_menu(is_premium_user=is_prem),
        parse_mode="HTML"
    )
