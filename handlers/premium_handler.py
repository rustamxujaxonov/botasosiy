"""
premium_handler.py
Tuzatishlar:
- cancel_payment → show_main_menu to'g'ri chaqiriladi
- PaymentState.waiting_receipt da barcha text xabarlar ushlanadi
"""

import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import PREMIUM_PLANS, PAYMENT_CARD_NUMBER, PAYMENT_CARD_OWNER
from database import create_payment_request, is_premium, update_payment_status
from keyboards import kb_premium_plans, kb_payment_sent

logger = logging.getLogger(__name__)
router = Router()


class PaymentState(StatesGroup):
    waiting_receipt = State()


async def show_premium_info(message: Message):
    text = (
        "⭐ <b>Premium obuna</b>\n\n"
        "Premium obuna bilan siz:\n"
        "👧 Qiz yoki 👦 Yigitlarni alohida qidirasiz\n"
        "📋 Muloqotchi profil ma'lumotlarini ko'rasiz\n"
        "🚀 Ustuvor qidirish navbati\n\n"
        "💰 <b>Obuna rejalari:</b>\n\n"
    )
    for plan_id, plan in PREMIUM_PLANS.items():
        text += f"{plan['emoji']} {plan['label']}: <b>{plan['price']:,} UZS</b>\n"

    text += "\n👇 Kerakli rejani tanlang:"
    await message.answer(text, reply_markup=kb_premium_plans())


# ============================================================
# REJA TANLASH
# ============================================================

@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: CallbackQuery, state: FSMContext):
    plan_id = callback.data.replace("buy_", "")
    plan = PREMIUM_PLANS.get(plan_id)

    if not plan:
        await callback.answer("❌ Reja topilmadi", show_alert=True)
        return

    await state.set_state(PaymentState.waiting_receipt)
    await state.update_data(selected_plan=plan_id)

    await callback.message.edit_text(
        f"💳 <b>{plan['emoji']} {plan['label']} — {plan['price']:,} UZS</b>\n\n"
        f"To'lov amalga oshirish uchun quyidagi karta raqamiga pul o'tkazing:\n\n"
        f"🏦 <b>Karta raqami:</b>\n"
        f"<code>{PAYMENT_CARD_NUMBER}</code>\n\n"
        f"👤 <b>Karta egasi:</b>\n"
        f"<code>{PAYMENT_CARD_OWNER}</code>\n\n"
        f"📸 To'lovni amalga oshirgach, <b>chek rasmini</b> shu yerga yuboring.\n"
        f"Admin 5–30 daqiqa ichida obunangizni faollashtiradi.\n\n"
        f"⬇️ Chek rasmini yuboring:",
        reply_markup=kb_payment_sent()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ To'lov bekor qilindi.")
    except Exception:
        pass

    from handlers.menu_handler import send_main_menu
    await send_main_menu(callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "receipt_sent")
async def receipt_sent_info(callback: CallbackQuery):
    await callback.answer(
        "📸 Iltimos, chek rasmini to'g'ridan-to'g'ri shu chatga yuboring.",
        show_alert=True
    )


# ============================================================
# CHEK QABUL QILISH
# ============================================================

@router.message(PaymentState.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext):
    data    = await state.get_data()
    plan_id = data.get("selected_plan")
    plan    = PREMIUM_PLANS.get(plan_id)

    if not plan:
        await message.answer("❌ Reja topilmadi. Iltimos, qayta urinib ko'ring.")
        await state.clear()
        return

    photo_file_id = message.photo[-1].file_id
    request_id = await create_payment_request(
        user_id=message.from_user.id,
        plan=plan_id,
        photo_file_id=photo_file_id,
        message_id=message.message_id
    )

    await _send_to_admin(message, request_id, plan_id, plan, photo_file_id)
    await state.clear()

    await message.answer(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "⏳ Admin tekshirib, obunangizni faollashtiradi.\n"
        "Odatda bu 5–30 daqiqa ichida amalga oshiriladi.\n\n"
        "Obuna faollashtirilgach, xabar yuboriladi."
    )

    from handlers.menu_handler import show_main_menu
    await show_main_menu(message, message.from_user.id)


@router.message(PaymentState.waiting_receipt)
async def receipt_not_photo(message: Message):
    """Rasm bo'lmagan har qanday xabar"""
    await message.answer(
        "📸 Iltimos, chek <b>rasmini</b> yuboring (photo ko'rinishida)."
    )


# ============================================================
# ADMIN GURUHIGA YUBORISH
# ============================================================

async def _send_to_admin(
    message: Message, request_id: int, plan_id: str,
    plan: dict, photo_file_id: str
):
    from config import ADMIN_GROUP_ID
    from keyboards import kb_admin_approve

    user = message.from_user
    username_text = f"@{user.username}" if user.username else "Username yo'q"

    caption = (
        f"💳 <b>Yangi to'lov so'rovi #{request_id}</b>\n\n"
        f"👤 Foydalanuvchi: {user.full_name}\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"📦 Reja: {plan['emoji']} {plan['label']} — {plan['price']:,} UZS\n\n"
        f"✅ Tasdiqlash uchun tugmani bosing:"
    )

    try:
        sent = await message.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=kb_admin_approve(request_id, user.id, plan_id)
        )
        await update_payment_status(request_id, "pending", sent.message_id)
    except Exception as e:
        logger.error(f"Admin guruhiga yuborishda xato: {e}")
