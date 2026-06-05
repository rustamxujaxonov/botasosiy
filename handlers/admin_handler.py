import logging
from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, PREMIUM_PLANS
from database import (
    get_payment_request, update_payment_status,
    grant_premium, get_user
)

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(Filter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        user_id = message.from_user.id
        return user_id in ADMIN_IDS


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    parts = callback.data.split("_")
    # approve_{request_id}_{user_id}_{plan_id}
    if len(parts) != 4:
        await callback.answer("❌ Noto'g'ri format", show_alert=True)
        return

    _, request_id_str, user_id_str, plan_id = parts
    request_id = int(request_id_str)
    user_id = int(user_id_str)

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

    # Premium berish
    await grant_premium(
        user_id=user_id,
        plan=plan_id,
        days=plan["days"],
        admin_id=callback.from_user.id
    )
    await update_payment_status(request_id, "approved")

    # Admin guruhda xabarni yangilash
    await callback.message.edit_caption(
        callback.message.caption +
        f"\n\n✅ <b>TASDIQLANDI</b> — {plan['emoji']} {plan['label']} berildi\n"
        f"👤 Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    try:
        user = await get_user(user_id)
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"✅ Premium obunangiz faollashtirildi!\n\n"
                f"{plan['emoji']} <b>{plan['label']}</b> obuna faol\n"
                f"⏱ Muddat: {plan['days']} kun\n\n"
                f"Endi premium funksiyalardan foydalanishingiz mumkin! 🚀"
            ),
            parse_mode="HTML"
        )

        # Asosiy menyuni qayta yuborish
        from database import is_premium
        from keyboards import kb_main_menu
        await callback.bot.send_message(
            chat_id=user_id,
            text="⬇️ Asosiy menyu:",
            reply_markup=kb_main_menu(is_premium_user=True)
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")

    await callback.answer("✅ Premium berildi!", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    parts = callback.data.split("_")
    # reject_{request_id}_{user_id}
    if len(parts) != 3:
        await callback.answer("❌ Noto'g'ri format", show_alert=True)
        return

    _, request_id_str, user_id_str = parts
    request_id = int(request_id_str)
    user_id = int(user_id_str)

    request = await get_payment_request(request_id)
    if not request:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if request["status"] != "pending":
        await callback.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await update_payment_status(request_id, "rejected")

    # Admin guruhda xabarni yangilash
    await callback.message.edit_caption(
        callback.message.caption +
        f"\n\n❌ <b>RAD ETILDI</b>\n"
        f"👤 Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>To'lovingiz rad etildi.</b>\n\n"
                "Sabab: Chek tasdiqlashdan o'tmadi yoki noto'g'ri yuborildi.\n\n"
                "❓ Muammo bo'lsa, admin bilan bog'laning."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")

    await callback.answer("❌ Rad etildi!", show_alert=True)
