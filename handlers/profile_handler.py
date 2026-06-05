"""
profile_handler.py
Tuzatishlar:
- show_profile_message ortiqcha premium check olib tashlandi
- back_main to'g'ri ishlaydi
- timezone-aware datetime comparison
"""

import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import get_user, update_profile, is_premium, get_premium_info
from keyboards import (
    kb_profile_edit, kb_edit_gender, kb_edit_regions,
    kb_back_profile
)

logger = logging.getLogger(__name__)
router = Router()


class EditProfile(StatesGroup):
    age  = State()
    name = State()


def _profile_text(user: dict, premium: bool, prem_info: dict = None) -> str:
    gender_text  = "👦 Yigit" if user.get("gender") == "male" else "👧 Qiz"
    premium_text = "✅ Faol" if premium else "❌ Faol emas"

    premium_until = ""
    if premium and prem_info:
        try:
            expires = datetime.fromisoformat(prem_info["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            premium_until = f"\n⏱ Muddat: <b>{expires.strftime('%d.%m.%Y %H:%M')}</b>"
        except Exception:
            pass

    return (
        f"👤 <b>Profil ma'lumotlari</b>\n\n"
        f"🏷 Taxallus: <b>{user.get('display_name', '—')}</b>\n"
        f"🚻 Jins: <b>{gender_text}</b>\n"
        f"🔢 Yosh: <b>{user.get('age', '—')}</b>\n"
        f"📍 Viloyat: <b>{user.get('region', '—')}</b>\n\n"
        f"💎 Premium: {premium_text}{premium_until}\n\n"
        f"🔧 Nimani o'zgartirmoqchisiz?"
    )


@router.message(F.text == "👤 Profil sozlamalari")
async def show_profile(message: Message, state: FSMContext):
    await state.clear()
    user_id  = message.from_user.id
    user     = await get_user(user_id)
    premium  = await is_premium(user_id)
    prem_info = await get_premium_info(user_id) if premium else None

    await message.answer(
        _profile_text(user, premium, prem_info),
        reply_markup=kb_profile_edit()
    )


# ============================================================
# JINS TAHRIRLASH
# ============================================================

@router.callback_query(F.data == "edit_gender")
async def edit_gender_prompt(callback: CallbackQuery):
    await callback.message.edit_text(
        "🚻 Yangi jinsingizni tanlang:",
        reply_markup=kb_edit_gender()
    )
    await callback.answer()


@router.callback_query(F.data.in_({"edit_gender_male", "edit_gender_female"}))
async def edit_gender_save(callback: CallbackQuery):
    gender      = "male" if callback.data == "edit_gender_male" else "female"
    gender_text = "👦 Yigit" if gender == "male" else "👧 Qiz"

    await update_profile(callback.from_user.id, gender=gender)
    await callback.answer(f"✅ Jins {gender_text} ga o'zgartirildi!", show_alert=False)
    await _refresh_profile(callback)


# ============================================================
# YOSH TAHRIRLASH
# ============================================================

@router.callback_query(F.data == "edit_age")
async def edit_age_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.age)
    await callback.message.edit_text(
        "🔢 Yangi yoshingizni kiriting (raqam bilan):\n<i>Masalan: 22</i>",
        reply_markup=kb_back_profile()
    )
    await callback.answer()


@router.message(EditProfile.age)
async def edit_age_save(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    if not text.isdigit():
        await message.answer("❗ Faqat raqam kiriting.", reply_markup=kb_back_profile())
        return

    age = int(text)
    if age < 14 or age > 80:
        await message.answer("❗ Yosh 14 dan 80 gacha bo'lishi kerak.", reply_markup=kb_back_profile())
        return

    await update_profile(message.from_user.id, age=age)
    await state.clear()
    await message.answer(f"✅ Yosh <b>{age}</b> ga o'zgartirildi!")
    await _send_profile(message)


# ============================================================
# VILOYAT TAHRIRLASH
# ============================================================

@router.callback_query(F.data == "edit_region")
async def edit_region_prompt(callback: CallbackQuery):
    await callback.message.edit_text(
        "📍 Yangi viloyatingizni tanlang:",
        reply_markup=kb_edit_regions()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_region_"))
async def edit_region_save(callback: CallbackQuery):
    region = callback.data.replace("edit_region_", "")
    await update_profile(callback.from_user.id, region=region)
    await callback.answer(f"✅ Viloyat {region} ga o'zgartirildi!", show_alert=False)
    await _refresh_profile(callback)


# ============================================================
# ISM TAHRIRLASH
# ============================================================

@router.callback_query(F.data == "edit_name")
async def edit_name_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditProfile.name)
    await callback.message.edit_text(
        "🏷 Yangi taxallusingizni kiriting:\n<i>2–20 ta harf</i>",
        reply_markup=kb_back_profile()
    )
    await callback.answer()


@router.message(EditProfile.name)
async def edit_name_save(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""

    if len(name) < 2:
        await message.answer("❗ Taxallus kamida 2 ta harfdan iborat bo'lsin.")
        return
    if len(name) > 20:
        await message.answer("❗ Taxallus 20 ta harfdan oshmasin.")
        return

    await update_profile(message.from_user.id, display_name=name)
    await state.clear()
    await message.answer(f"✅ Taxallus <b>{name}</b> ga o'zgartirildi!")
    await _send_profile(message)


# ============================================================
# NAVIGATSIYA
# ============================================================

@router.callback_query(F.data == "back_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _refresh_profile(callback)
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.menu_handler import send_main_menu
    await send_main_menu(callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


async def _refresh_profile(callback: CallbackQuery):
    user_id   = callback.from_user.id
    user      = await get_user(user_id)
    premium   = await is_premium(user_id)
    prem_info = await get_premium_info(user_id) if premium else None
    text      = _profile_text(user, premium, prem_info)

    try:
        await callback.message.edit_text(text, reply_markup=kb_profile_edit())
    except Exception:
        await callback.message.answer(text, reply_markup=kb_profile_edit())


async def _send_profile(message: Message):
    user_id   = message.from_user.id
    user      = await get_user(user_id)
    premium   = await is_premium(user_id)
    prem_info = await get_premium_info(user_id) if premium else None

    await message.answer(
        _profile_text(user, premium, prem_info),
        reply_markup=kb_profile_edit()
    )
