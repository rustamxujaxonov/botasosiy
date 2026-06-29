"""
handlers/referral_handler.py — Referral tizimi

Qanday ishlaydi:
1. /start ref_123456 → start_handler referrer_id ni saqlaydi
2. Ro'yxatdan o'tgach → confirm_referral_after_registration chaqiriladi
3. Har 5 referralda → 1 kunlik premium avtomatik beriladi
4. "👥 Referral" tugmasi → o'z havolasini ko'rish
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import database as db

logger = logging.getLogger(__name__)
router = Router()

REFERRAL_NEEDED = 5  # nechi do'st kerak = 1 kunlik premium


# ============================================================
# RO'YXATDAN O'TGANDAN KEYIN CHAQIRILADI
# (registration_handler.py dan import qilinadi)
# ============================================================

async def confirm_referral_after_registration(new_user_id: int, inviter_id: int, bot: Bot):
    """
    Yangi user ro'yxatdan o'tgandan keyin chaqiriladi.
    registration_handler.py ning reg_region funksiyasida ishlatiladi.
    """
    if inviter_id == new_user_id:
        return

    added = await db.add_referral(inviter_id, new_user_id)
    if not added:
        return  # allaqachon qayd etilgan

    count = await db.get_referral_count(inviter_id)
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED)

    # Har 5 ta to'lganda premium ber
    if count % REFERRAL_NEEDED == 0:
        await db.check_and_grant_referral_premium(inviter_id, bot)
    else:
        # Taklif qilganga progress xabari
        try:
            await bot.send_message(
                chat_id=inviter_id,
                text=(
                    f"🎉 <b>Do'stingiz botga qo'shildi!</b>\n\n"
                    f"👥 Referrallaringiz: <b>{count}</b> ta\n"
                    f"🎁 Premiumgacha: yana <b>{remaining}</b> ta do'st kerak"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Referral xabari yuborib bo'lmadi {inviter_id}: {e}")


# ============================================================
# REFERRAL SAHIFASI — "👥 Referral" tugmasi
# ============================================================

@router.message(F.text == "👥 Referral")
async def referral_page(message: Message):
    user_id = message.from_user.id
    count = await db.get_referral_count(user_id)
    milestones_earned = count // REFERRAL_NEEDED
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED) if count % REFERRAL_NEEDED != 0 else REFERRAL_NEEDED

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await message.answer(
        f"👥 <b>Referral tizimi</b>\n\n"
        f"Har <b>{REFERRAL_NEEDED} ta</b> do'st taklif qiling → "
        f"<b>1 kunlik premium</b> oling!\n\n"
        f"📊 Sizning statistikangiz:\n"
        f"├ Taklif qilinganlar: <b>{count}</b> ta\n"
        f"├ Olingan premiumlar: <b>{milestones_earned}</b> ta\n"
        f"└ Keyingisiga: yana <b>{remaining}</b> ta\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"Quyidagi tugma orqali do'stlaringizga yuboring 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Do'stlarga yuborish",
                url=f"https://t.me/share/url?url={ref_link}&text=Yangi%20do%27stlar%20topish%20uchun%20qo%27shiling%21%20%F0%9F%98%8A"
            )],
            [InlineKeyboardButton(
                text="🔄 Yangilash",
                callback_data="referral_refresh"
            )],
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "referral_refresh")
async def referral_refresh(callback):
    user_id = callback.from_user.id
    count = await db.get_referral_count(user_id)
    milestones_earned = count // REFERRAL_NEEDED
    remaining = REFERRAL_NEEDED - (count % REFERRAL_NEEDED) if count % REFERRAL_NEEDED != 0 else REFERRAL_NEEDED

    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await callback.message.edit_text(
        f"👥 <b>Referral tizimi</b>\n\n"
        f"Har <b>{REFERRAL_NEEDED} ta</b> do'st taklif qiling → "
        f"<b>1 kunlik premium</b> oling!\n\n"
        f"📊 Sizning statistikangiz:\n"
        f"├ Taklif qilinganlar: <b>{count}</b> ta\n"
        f"├ Olingan premiumlar: <b>{milestones_earned}</b> ta\n"
        f"└ Keyingisiga: yana <b>{remaining}</b> ta\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Do'stlarga yuborish",
                url=f"https://t.me/share/url?url={ref_link}&text=Yangi%20do%27stlar%20topish%20uchun%20qo%27shiling%21%20%F0%9F%98%8A"
            )],
            [InlineKeyboardButton(
                text="🔄 Yangilash",
                callback_data="referral_refresh"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer("✅ Yangilandi!")
