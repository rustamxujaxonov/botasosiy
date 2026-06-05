import os
from dotenv import load_dotenv

load_dotenv()

# ===== BOT =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ===== DATABASE (Railway avtomatik beradi) =====
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/dbname")

# Railway ba'zan postgresql:// beradi — asyncpg uchun to'g'rilash
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ===== KANAL =====
CHANNEL_ID   = os.getenv("CHANNEL_ID",   "@your_channel")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")

# ===== ADMIN =====
ADMIN_GROUP_ID  = int(os.getenv("ADMIN_GROUP_ID", "-1001234567890"))
ADMIN_IDS_STR   = os.getenv("ADMIN_IDS", "123456789")
ADMIN_IDS       = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]

# ===== TO'LOV =====
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD",  "8600 0000 0000 0000")
PAYMENT_CARD_OWNER  = os.getenv("PAYMENT_OWNER", "Ism Familiya")

# ===== PREMIUM REJALARI =====
PREMIUM_PLANS = {
    "1kun":  {"label": "1 kunlik",   "price": 5_000,  "days": 1,  "emoji": "🌟"},
    "3kun":  {"label": "3 kunlik",   "price": 7_000,  "days": 3,  "emoji": "💫"},
    "7kun":  {"label": "1 haftalik", "price": 15_000, "days": 7,  "emoji": "⭐"},
    "30kun": {"label": "1 oylik",    "price": 30_000, "days": 30, "emoji": "👑"},
}

# ===== VILOYATLAR =====
REGIONS = [
    "Toshkent shahri", "Toshkent viloyati", "Samarqand",
    "Buxoro", "Farg'ona", "Andijon", "Namangan",
    "Qashqadaryo", "Surxondaryo", "Xorazm",
    "Navoiy", "Jizzax", "Sirdaryo", "Qoraqalpog'iston",
]
