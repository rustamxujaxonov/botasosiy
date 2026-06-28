"""
registration_handler.py
Tuzatishlar:
- start_registration endi message emas, bot + chat_id qabul qiladi
- State check EditProfile bilan to'g'ri ishlaydi
- FSM to'g'ri tartibda: gender → name → age → region
"""

import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import complete_registration
from keyboards import kb_gender, kb_regions

logger = logging.getLogger(__name__)
router = Router()


class RegState(StatesGroup):
    gender = State()
    name   = State()
    age    = State()
    region = State()


# ============================================================
# GENDER — birinchi qadam
# ============================================================

@router.callback_query(F.data.in_({"gender_male", "gender_female"}))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    current = await state.get_state()

    # Profil tahrirlash state'i bo'lsa — bu handler uchun emas
    if current and "EditProfile" in str(current):
        return

    # Ro'yxatdan o'tish boshlangan bo'lsa yoki hech qanday state yo'q bo'lsa
    gender = "male" if callback.data == "gender_male" else "female"
    gender_text = "👦 Yigit" if gender == "male" else "👧 Qiz"

    await state.update_data(gender=gender)
    await state.set_state(RegState.name)

    await callback.message.edit_text(
        f"✅ Jins: <b>{gender_text}</b>\n\n"
        "🏷 Endi o'zingizga <b>taxallus</b> (laqab) kiriting:\n"
        "<i>Bu botda ko'rinadigan ism. Haqiqiy ismingizni yozmasligingiz mumkin.</i>"
    )
    await callback.answer()


# ============================================================
# NAME
# ============================================================

@router.message(RegState.name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""

    if len(name) < 2:
        await message.answer("❗ Taxallus kamida 2 ta harfdan iborat bo'lsin.")
        return
    if len(name) > 20:
        await message.answer("❗ Taxallus 20 ta harfdan oshmasin.")
        return

    await state.update_data(display_name=name)
    await state.set_state(RegState.age)

    await message.answer(
        f"✅ Taxallus: <b>{name}</b>\n\n"
        "🔢 Yoshingizni kiriting (raqam bilan):\n"
        "<i>Masalan: 18</i>"
    )


# ============================================================
# AGE
# ============================================================

@router.message(RegState.age)
async def reg_age(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    if not text.isdigit():
        await message.answer("❗ Iltimos, yoshingizni faqat raqam bilan kiriting.")
        return

    age = int(text)
    if age < 14 or age > 80:
        await message.answer("❗ Yosh 14 dan 80 gacha bo'lishi kerak.")
        return

    await state.update_data(age=age)
    await state.set_state(RegState.region)

    await message.answer(
        f"✅ Yosh: <b>{age}</b>\n\n"
        "📍 Viloyatingizni tanlang:",
        reply_markup=kb_regions()
    )


# ============================================================
# REGION — oxirgi qadam
# ============================================================

@router.callback_query(RegState.region, F.data.startswith("region_"))
async def reg_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.replace("region_", "")
    data = await state.get_data()

    gender       = data.get("gender", "male")
    display_name = data.get("display_name", "Anonim")
    age          = data.get("age", 18)
    gender_text  = "👦 Yigit" if gender == "male" else "👧 Qiz"

    await complete_registration(
        user_id=callback.from_user.id,
        gender=gender,
        display_name=display_name,
        age=age,
        region=region
    )
    await state.clear()

    await callback.message.edit_text(
        f"🎉 <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
        f"👤 Taxallus: <b>{display_name}</b>\n"
        f"🚻 Jins: <b>{gender_text}</b>\n"
        f"🔢 Yosh: <b>{age}</b>\n"
        f"📍 Viloyat: <b>{region}</b>\n\n"
        f"✅ Endi botdan foydalanishingiz mumkin!"
    )
    # complete_registration dan keyin:
state_data = await state.get_data()
referrer_id = state_data.get("pending_referrer_id")
if referrer_id:
    from handlers.referral_handler import confirm_referral_after_registration
    await confirm_referral_after_registration(user_id, referrer_id, bot)
    from handlers.menu_handler import send_main_menu
    await send_main_menu(callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()
