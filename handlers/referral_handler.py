"""
handlers/referral_handler.py — Referral tizimi

Qanday ishlaydi:
- /start ref_123456 → yangi user referral orqali keldi
- "👥 Referral" tugmasi → o'z havolasini ko'rish va hisobni tekshirish
- Har 5 do'st → 1 kunlik premium avtomatik
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db

logger = logging.getLogger(__name__)
router = Router()

REFERRAL_NEEDED = 5  # nechi do'st kerak


def kb_referral(user_id: int, count: int):
    """Referral tugmalari"""
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED)
    if count > 0 and count % REFERRAL_NEEDED == 0:
        remaining = REFERRAL_NEEDED

    bot_username_placeholder = "Tanishuvlar_uz_bot"  # bot username

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📤 Havolani ulashish ({count}/{REFERRAL_NEEDED})",
            switch_inline_query=f"Do'stingizni taklif qiling! Men bu botdan foydalanmoqdaman 👉 @{bot_username_placeholder}?start=ref_{user_id}"
        )],
        [InlineKeyboardButton(
            text="🔄 Hisobni yangilash",
            callback_data="referral_check"
        )],
    ])


async def process_referral(inviter_id: int, new_user_id: int, bot: Bot):
    """
    Yangi user ro'yxatdan o'tgandan keyin chaqiriladi.
    start_handler yoki registration_handler dan import qilib ishlatiladi.
    """
    if inviter_id == new_user_id:
        return

    added = await db.add_referral(inviter_id, new_user_id)
    if not added:
        return

    count = await db.get_referral_count(inviter_id)
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED)

    # Taklif qilganga xabar
    try:
        if count % REFERRAL_NEEDED == 0:
            # Premium beriladi — check_and_grant_referral_premium ichida xabar ketadi
            await db.check_and_grant_referral_premium(inviter_id, bot)
        else:
            await bot.send_message(
                chat_id=inviter_id,
                text=(
                    f"🎉 Do'stingiz botga qo'shildi!\n\n"
                    f"👥 Sizning referrallaringiz: <b>{count}</b>\n"
                    f"🎁 Premiumgacha: yana <b>{remaining}</b> ta do'st kerak"
                ),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Referral xabari yuborib bo'lmadi {inviter_id}: {e}")


# ============================================================
# REFERRAL SAHIFASI
# ============================================================

@router.message(F.text == "👥 Referral")
async def referral_page(message: Message):
    user_id = message.from_user.id
    count = await db.get_referral_count(user_id)
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED)

    # Bot usernameni olish
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    milestones_earned = count // REFERRAL_NEEDED

    text = (
        f"👥 <b>Referral tizimi</b>\n\n"
        f"Har <b>{REFERRAL_NEEDED} ta</b> do'st taklif qilsangiz "
        f"<b>1 kunlik premium</b> olasiz!\n\n"
        f"📊 Sizning statistikangiz:\n"
        f"├ Taklif qilinganlar: <b>{count}</b> ta\n"
        f"├ Olingan premiumlar: <b>{milestones_earned}</b> ta\n"
        f"└ Keyingisiga: yana <b>{remaining if count % REFERRAL_NEEDED != 0 else REFERRAL_NEEDED}</b> ta\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"Yuqoridagi tugma orqali do'stlaringizga yuboring 👇"
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📤 Do'stlarga yuborish",
                url=f"https://t.me/share/url?url={ref_link}&text=Meni%20ushbu%20botga%20qo%27shiling%21%20Yangi%20do%27stlar%20topasiz%20%F0%9F%98%8A"
            )],
            [InlineKeyboardButton(
                text="🔄 Hisobni yangilash",
                callback_data="referral_check"
            )],
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "referral_check")
async def referral_check(callback):
    user_id = callback.from_user.id
    count = await db.get_referral_count(user_id)
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED)
    milestones_earned = count // REFERRAL_NEEDED

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    text = (
        f"👥 <b>Referral tizimi</b>\n\n"
        f"Har <b>{REFERRAL_NEEDED} ta</b> do'st taklif qilsangiz "
        f"<b>1 kunlik premium</b> olasiz!\n\n"
        f"📊 Sizning statistikangiz:\n"
        f"├ Taklif qilinganlar: <b>{count}</b> ta\n"
        f"├ Olingan premiumlar: <b>{milestones_earned}</b> ta\n"
        f"└ Keyingisiga: yana <b>{remaining if count % REFERRAL_NEEDED != 0 else REFERRAL_NEEDED}</b> ta\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📤 Do'stlarga yuborish",
                url=f"https://t.me/share/url?url={ref_link}&text=Meni%20ushbu%20botga%20qo%27shiling%21%20Yangi%20do%27stlar%20topasiz%20%F0%9F%98%8A"
            )],
            [InlineKeyboardButton(
                text="🔄 Hisobni yangilash",
                callback_data="referral_check"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer("✅ Yangilandi!")
