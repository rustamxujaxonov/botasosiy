"""
menu_handler.py

Tuzatishlar:
- ✅ Barcha qidiruv knopkalari handlerlari
- ✅ Premium taklif xabariga referral tugmasi qo'shildi
"""

import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database import get_user, is_premium
from keyboards import kb_main_menu, kb_premium_plans
from handlers.search_handler import start_search

logger = logging.getLogger(__name__)
router = Router()


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

async def send_main_menu(bot: Bot, chat_id: int, user_id: int):
    user = await get_user(user_id)
    premium = await is_premium(user_id)

    if not user:
        await bot.send_message(chat_id=chat_id, text="❗ Xato yuz berdi. /start bosing.")
        return

    gender_emoji = "👦" if user.get("gender") == "male" else "👧"
    premium_badge = "⭐ Premium" if premium else "🆓 Tekin"

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🏠 <b>Asosiy menyu</b>\n\n"
            f"{gender_emoji} {user.get('display_name', 'Foydalanuvchi')} | "
            f"🔢 {user.get('age', '?')} yosh | "
            f"📍 {user.get('region', '—')}\n"
            f"💎 Holat: {premium_badge}\n\n"
            f"Nima qilmoqchisiz?"
        ),
        reply_markup=kb_main_menu(is_premium_user=premium),
        parse_mode="HTML"
    )


async def show_main_menu(message: Message, user_id: int):
    await send_main_menu(message.bot, message.chat.id, user_id)


def kb_premium_with_referral():
    """Premium sotib olish + referral orqali olish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Premium sotib olish",
            callback_data="show_premium_plans"
        )],
        [InlineKeyboardButton(
            text="👥 5 do'st taklif qilib BEPUL olish",
            callback_data="show_referral"
        )],
    ])


# ============================================================
# ASOSIY MENYU
# ============================================================

@router.message(F.text == "🏠 Asosiy menyu")
async def main_menu_handler(message: Message):
    await show_main_menu(message, message.from_user.id)


# ============================================================
# QIDIRUV KNOPKALARI
# ============================================================

@router.message(F.text == "🔍 Muloqotchi qidirish")
async def menu_search_any(message: Message, state: FSMContext):
    await start_search(message, state, "any")


@router.message(F.text == "👧 Qiz qidirish")
async def menu_search_female(message: Message, state: FSMContext):
    await start_search(message, state, "female")


@router.message(F.text == "👦 Yigit qidirish")
async def menu_search_male(message: Message, state: FSMContext):
    await start_search(message, state, "male")


@router.message(F.text == "👧 Qiz qidirish ⭐")
async def menu_search_female_locked(message: Message):
    await message.answer(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )


@router.message(F.text == "👦 Yigit qidirish ⭐")
async def menu_search_male_locked(message: Message):
    await message.answer(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )


# ============================================================
# PREMIUM / REFERRAL CALLBACK
# ============================================================

@router.callback_query(F.data == "show_premium_plans")
async def cb_show_premium_plans(callback):
    await callback.message.edit_text(
        "💳 <b>Premium rejalar</b>\n\nQuyidan rejani tanlang:",
        reply_markup=kb_premium_plans(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_referral")
async def cb_show_referral(callback):
    import database as db
    user_id = callback.from_user.id
    count = await db.get_referral_count(user_id)
    remaining = 5 - (count % 5) if count % 5 != 0 else 5

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    await callback.message.edit_text(
        f"👥 <b>Referral orqali bepul premium!</b>\n\n"
        f"<b>5 ta do'st</b> taklif qiling → <b>1 kunlik premium</b> oling!\n\n"
        f"📊 Sizning holatiz:\n"
        f"├ Taklif qilinganlar: <b>{count}</b> ta\n"
        f"└ Premiumgacha: yana <b>{remaining}</b> ta\n\n"
        f"🔗 Sizning havolangiz:\n"
        f"<code>{ref_link}</code>\n\n"
        f"Quyidagi tugma orqali do'stlaringizga yuboring 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Do'stlarga yuborish",
                url=f"https://t.me/share/url?url={ref_link}&text=Yangi%20do%27stlar%20topish%20uchun%20qo%27shiling%21"
            )],
            [InlineKeyboardButton(
                text="🔄 Hisobni yangilash",
                callback_data="show_referral"
            )],
            [InlineKeyboardButton(
                text="⬅️ Orqaga",
                callback_data="back_to_premium_choice"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_premium_choice")
async def cb_back_to_premium_choice(callback):
    await callback.message.edit_text(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )
    await callback.answer()
