"""
menu_handler.py

Tuzatishlar:
- ✅ Barcha qidiruv knopkalari va asosiy menyuda majburiy obuna tekshiruvi integratsiya qilindi.
- ✅ Obunani tasdiqlash (check_subscription) callback handler'i qo'shildi.
- ✅ Aiogram turlaridan CallbackQuery importi to'g'rilandi.
"""

import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database import get_user, is_premium
from keyboards import kb_main_menu, kb_premium_plans
from handlers.search_handler import start_search

logger = logging.getLogger(__name__)
router = Router()

# ============================================================
# MAJBURIY OBUNA SOZLAMALARI
# ============================================================
# Bu yerga bot tekshirishi kerak bo'lgan kanallarni yozing.
# Bot ushbu kanallarda admin bo'lishi shart!
CHANNELS = ["@tanishuvlarbotichannel"] 


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi hamma majburiy kanallarga a'zo bo'lganini tekshiradi"""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logger.error(f"Kanal tekshirishda xatolik ({channel}): {e}")
            # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa xato bermasligi uchun ehtiyotkorlik
            return False
    return True


async def send_sub_keyboards(message: Message):
    """Obuna bo'lmagan foydalanuvchiga kanallar ro'yxatini ko'rsatish"""
    buttons = []
    for idx, ch in enumerate(CHANNELS, start=1):
        link = f"https://t.me/{ch.replace('@', '')}"
        buttons.append([InlineKeyboardButton(text=f"🔗 {idx}-kanalga a'zo bo'lish", url=link)])
    
    buttons.append([InlineKeyboardButton(text="🔄 Obunani tasdiqlash", callback_data="check_subscription")])
    kb_sub = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz shart!</b>\n\n"
        "A'zo bo'lib, keyin <i>Tasdiqlash</i> tugmasini bosing.",
        reply_markup=kb_sub,
        parse_mode="HTML"
    )


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
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await show_main_menu(message, message.from_user.id)


# ============================================================
# QIDIRUV KNOPKALARI
# ============================================================

@router.message(F.text == "🔍 Muloqotchi qidirish")
async def menu_search_any(message: Message, state: FSMContext):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await start_search(message, state, "any")


@router.message(F.text == "👧 Qiz qidirish")
async def menu_search_female(message: Message, state: FSMContext):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await start_search(message, state, "female")


@router.message(F.text == "👦 Yigit qidirish")
async def menu_search_male(message: Message, state: FSMContext):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await start_search(message, state, "male")


@router.message(F.text == "👧 Qiz qidirish ⭐")
async def menu_search_female_locked(message: Message):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await message.answer(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )


@router.message(F.text == "👦 Yigit qidirish ⭐")
async def menu_search_male_locked(message: Message):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await send_sub_keyboards(message)
        return
        
    await message.answer(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )


# ============================================================
# PREMIUM / REFERRAL / SUB CALLBACKS
# ============================================================

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery):
    """Foydalanuvchi obunani tasdiqlash tugmasini bosganda ishlaydi"""
    is_subbed = await check_user_subscription(callback.bot, callback.from_user.id)
    
    if is_subbed:
        try:
            await callback.message.delete()  # Kanallar ro'yxati matnini o'chirib tashlaymiz
        except Exception:
            pass
        # Asosiy menyuni yuboramiz
        await send_main_menu(callback.bot, callback.message.chat.id, callback.from_user.id)
        await callback.answer("🎉 Obuna tasdiqlandi! Asosiy menyuga xush kelibsiz.", show_alert=True)
    else:
        await callback.answer("❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)


@router.callback_query(F.data == "show_premium_plans")
async def cb_show_premium_plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 <b>Premium rejalar</b>\n\nQuyidan rejani tanlang:",
        reply_markup=kb_premium_plans(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_referral")
async def cb_show_referral(callback: CallbackQuery):
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
async def cb_back_to_premium_choice(callback: CallbackQuery):
    await callback.message.edit_text(
        "⭐ <b>Bu funksiya faqat premium foydalanuvchilar uchun!</b>\n\n"
        "Jins bo'yicha qidiruv — premium imkoniyat.\n\n"
        "Quyidan tanlang 👇",
        reply_markup=kb_premium_with_referral(),
        parse_mode="HTML"
    )
    await callback.answer()
