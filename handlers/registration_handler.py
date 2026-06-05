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
    name = State()
    age = State()
    region = State()


async def start_registration(message: Message):
    await message.answer(
        "📋 <b>Ro'yxatdan o'tish</b>\n\n"
        "Bu ma'lumotlar anonim saqlanadi va boshqalarga ko'rsatilmaydi.\n\n"
        "👤 Avval jinsingizni tanlang:",
        reply_markup=kb_gender(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.in_({"gender_male", "gender_female"}))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    current = await state.get_state()

    # Agar profil tahrirlash bo'lsa boshqa handler ishlaydi
    if current and "EditProfile" in str(current):
        return

    gender = "male" if callback.data == "gender_male" else "female"
    gender_text = "👦 Yigit" if gender == "male" else "👧 Qiz"

    await state.set_state(RegState.name)
    await state.update_data(gender=gender)

    await callback.message.edit_text(
        f"✅ Jins: <b>{gender_text}</b>\n\n"
        "🏷 Endi o'zingizga <b>taxallus</b> (laqab) kiriting:\n"
        "<i>Bu botda ko'rinadigan ism. Haqiqiy ismingizni yozmasligingiz mumkin.</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RegState.name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()

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
        "<i>Masalan: 18</i>",
        parse_mode="HTML"
    )


@router.message(RegState.age)
async def reg_age(message: Message, state: FSMContext):
    text = message.text.strip()

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
        reply_markup=kb_regions(),
        parse_mode="HTML"
    )


@router.callback_query(RegState.region, F.data.startswith("region_"))
async def reg_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.replace("region_", "")
    data = await state.get_data()

    gender = data.get("gender")
    display_name = data.get("display_name")
    age = data.get("age")
    gender_text = "👦 Yigit" if gender == "male" else "👧 Qiz"

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
        f"✅ Endi botdan foydalanishingiz mumkin!",
        parse_mode="HTML"
    )

    from handlers.menu_handler import show_main_menu
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()
