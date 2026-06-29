from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from config import PREMIUM_PLANS, CHANNEL_LINK, REGIONS


def kb_remove():
    return ReplyKeyboardRemove()


# ============================================================
# SUBSCRIPTION CHECK
# ============================================================

def kb_check_subscription():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")],
    ])


# ============================================================
# REGISTRATION
# ============================================================

def kb_gender():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👦 Yigit", callback_data="gender_male"),
            InlineKeyboardButton(text="👧 Qiz", callback_data="gender_female"),
        ]
    ])


def kb_regions():
    buttons = []
    row = []
    for i, region in enumerate(REGIONS):
        row.append(InlineKeyboardButton(text=region, callback_data=f"region_{region}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# MAIN MENU
# ============================================================

def kb_main_menu(is_premium_user: bool = False):
    keyboard = [
        [KeyboardButton(text="🔍 Muloqotchi qidirish")],
    ]
    if is_premium_user:
        keyboard.append([
            KeyboardButton(text="👧 Qiz qidirish"),
            KeyboardButton(text="👦 Yigit qidirish"),
        ])
    else:
        keyboard.append([
            KeyboardButton(text="👧 Qiz qidirish ⭐"),
            KeyboardButton(text="👦 Yigit qidirish ⭐"),
        ])
    keyboard.append([KeyboardButton(text="👤 Profil sozlamalari")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def kb_main_menu(is_premium_user: bool = False):
    keyboard = [
        [KeyboardButton(text="🔍 Muloqotchi qidirish")],
    ]
    if is_premium_user:
        keyboard.append([
            KeyboardButton(text="👧 Qiz qidirish"),
            KeyboardButton(text="👦 Yigit qidirish"),
        ])
    else:
        keyboard.append([
            KeyboardButton(text="👧 Qiz qidirish ⭐"),
            KeyboardButton(text="👦 Yigit qidirish ⭐"),
        ])
    keyboard.append([KeyboardButton(text="👤 Profil sozlamalari")])
    keyboard.append([KeyboardButton(text="👥 Referral")])  # ← QO'SHING
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
# ============================================================
# PREMIUM PLANS
# ============================================================

def kb_premium_plans():
    buttons = []
    for plan_id, plan in PREMIUM_PLANS.items():
        text = f"{plan['emoji']} {plan['label']} — {plan['price']:,} UZS"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"buy_{plan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_payment_sent():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Chekni yubordim", callback_data="receipt_sent")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment")],
    ])


# ============================================================
# ADMIN PANEL (chek tasdiqlash)
# ============================================================

def kb_admin_approve(request_id: int, user_id: int, plan: str):
    buttons = []
    for plan_id, plan_info in PREMIUM_PLANS.items():
        text = f"✅ {plan_info['emoji']} {plan_info['label']} ber"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"approve_{request_id}_{user_id}_{plan_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"reject_{request_id}_{user_id}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# CHAT CONTROLS
# ============================================================

def kb_in_chat():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Keyingisi"), KeyboardButton(text="🚫 Chatdan chiqish")],
        ],
        resize_keyboard=True
    )


def kb_stop_search():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Qidirishni to'xtatish")]],
        resize_keyboard=True
    )


# ============================================================
# PROFILE EDIT
# ============================================================

def kb_profile_edit():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚻 Jinsni o'zgartirish", callback_data="edit_gender")],
        [InlineKeyboardButton(text="🔢 Yoshni o'zgartirish", callback_data="edit_age")],
        [InlineKeyboardButton(text="📍 Hududni o'zgartirish", callback_data="edit_region")],
        [InlineKeyboardButton(text="🏷 Ismni o'zgartirish", callback_data="edit_name")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_main")],
    ])


def kb_edit_gender():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👦 Yigit", callback_data="edit_gender_male"),
            InlineKeyboardButton(text="👧 Qiz", callback_data="edit_gender_female"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_profile")],
    ])


def kb_edit_regions():
    buttons = []
    row = []
    for i, region in enumerate(REGIONS):
        row.append(InlineKeyboardButton(text=region, callback_data=f"edit_region_{region}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_back_profile():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_profile")]
    ])
