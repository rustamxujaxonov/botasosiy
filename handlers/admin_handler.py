"""
admin_handler.py
Tuzatishlar:
- parse_mode default bo'lganligi uchun olib tashlandi (bot.py da DefaultBotProperties bor)
- Xato callback_data format'i yaxshiroq handle qilinadi
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS, PREMIUM_PLANS
from database import (
    get_payment_request, update_payment_status,
    grant_premium, get_user
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    # approve_{request_id}_{user_id}_{plan_id}
    try:
        parts = callback.data.split("_", 3)
        # ['approve', request_id, user_id, plan_id]
        _, request_id_str, user_id_str, plan_id = parts
        request_id = int(request_id_str)
        user_id    = int(user_id_str)
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri format", show_alert=True)
        return

    request = await get_payment_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if request["status"] != "pending":
        await callback.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    plan = PREMIUM_PLANS.get(plan_id)
    if not plan:
        await callback.answer("❌ Reja topilmadi!", show_alert=True)
        return

    await grant_premium(
        user_id=user_id,
        plan=plan_id,
        days=plan["days"],
        admin_id=callback.from_user.id
    )
    await update_payment_status(request_id, "approved")

    # Admin xabarini yangilash
    try:
        new_caption = (
            (callback.message.caption or "") +
            f"\n\n✅ <b>TASDIQLANDI</b> — {plan['emoji']} {plan['label']} berildi\n"
            f"👤 Admin: {callback.from_user.full_name}"
        )
        await callback.message.edit_caption(new_caption)
    except Exception as e:
        logger.error(f"Admin caption yangilashda xato: {e}")

    # Foydalanuvchiga xabar
    try:
        from keyboards import kb_main_menu
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"✅ Premium obunangiz faollashtirildi!\n\n"
                f"{plan['emoji']} <b>{plan['label']}</b> obuna faol\n"
                f"⏱ Muddat: {plan['days']} kun\n\n"
                f"Endi premium funksiyalardan foydalanishingiz mumkin! 🚀"
            )
        )
        await callback.bot.send_message(
            chat_id=user_id,
            text="⬇️ Asosiy menyu:",
            reply_markup=kb_main_menu(is_premium_user=True)
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga premium xabari yuborishda xato: {e}")

    await callback.answer("✅ Premium berildi!", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    # reject_{request_id}_{user_id}
    try:
        parts      = callback.data.split("_", 2)
        _, request_id_str, user_id_str = parts
        request_id = int(request_id_str)
        user_id    = int(user_id_str)
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri format", show_alert=True)
        return

    request = await get_payment_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if request["status"] != "pending":
        await callback.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await update_payment_status(request_id, "rejected")

    try:
        new_caption = (
            (callback.message.caption or "") +
            f"\n\n❌ <b>RAD ETILDI</b>\n"
            f"👤 Admin: {callback.from_user.full_name}"
        )
        await callback.message.edit_caption(new_caption)
    except Exception as e:
        logger.error(f"Admin caption yangilashda xato: {e}")

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>To'lovingiz rad etildi.</b>\n\n"
                "Sabab: Chek tasdiqlashdan o'tmadi yoki noto'g'ri yuborildi.\n\n"
                "❓ Muammo bo'lsa, admin bilan bog'laning."
            )
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga rad xabari yuborishda xato: {e}")

    await callback.answer("❌ Rad etildi!", show_alert=True)
