# 💬 Anonim Chat Bot — Railway + PostgreSQL

## 🗂 Fayl tuzilmasi
```
anonim_chat_bot/
├── bot.py                      # Ishga tushirish
├── config.py                   # Barcha sozlamalar (env dan o'qiydi)
├── database.py                 # SQLAlchemy 2.x async ORM
├── keyboards.py                # Tugmalar
├── requirements.txt
├── .env.example
│
├── migrations/                 # Alembic migratsiyalar
│   ├── env.py
│   └── versions/
│
└── handlers/
    ├── start_handler.py        # /start, kanal obunasi
    ├── registration_handler.py # FSM: jins→taxallus→yosh→viloyat
    ├── menu_handler.py         # Asosiy menyu
    ├── search_handler.py       # Qidirish (tekin/premium)
    ├── chat_handler.py         # Xabarlarni relay qilish
    ├── premium_handler.py      # Narxlar, to'lov, chek qabul
    ├── admin_handler.py        # Chekni tasdiqlash/rad etish
    └── profile_handler.py      # Profil tahrirlash
```

---

## 🚀 Railway ga deploy

### 1. Railway.app da loyiha oching
1. [railway.app](https://railway.app) → **New Project**
2. **Deploy from GitHub repo** → reponi tanlang

### 2. PostgreSQL qo'shing
1. Loyiha ichida → **+ New** → **Database** → **PostgreSQL**
2. Railway avtomatik `DATABASE_URL` environment variable beradi

### 3. Environment variables qo'shing
Railway dashboard → **Variables** bo'limiga:

| Variable | Qiymat |
|----------|--------|
| `BOT_TOKEN` | BotFather dan olingan token |
| `CHANNEL_ID` | `@kanal_username` |
| `CHANNEL_LINK` | `https://t.me/kanal_username` |
| `ADMIN_GROUP_ID` | Guruh ID (manfiy son) |
| `ADMIN_IDS` | `123456789,987654321` |
| `PAYMENT_CARD` | `8600 xxxx xxxx xxxx` |
| `PAYMENT_OWNER` | Karta egasining ismi |

> `DATABASE_URL` ni qo'shishga hojat yo'q — Railway avtomatik ulaydi!

### 4. Start command
Railway → **Settings** → **Deploy** → **Start Command:**
```
python bot.py
```

### 5. Migratsiya (birinchi marta)
Railway → **Shell** yoki local terminalda:
```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## 💻 Lokalda ishga tushirish

```bash
# 1. Kutubxonalar
pip install -r requirements.txt

# 2. .env yarating
cp .env.example .env
# .env faylini to'ldiring

# 3. Migratsiya
alembic revision --autogenerate -m "initial"
alembic upgrade head

# 4. Botni ishga tushiring
python bot.py
```

---

## ⚙️ Funksiyalar

### 🆓 Tekin
- Kanal obunasi tekshiruvi
- Ro'yxatdan o'tish (jins, taxallus, yosh, viloyat)
- Anonim muloqot (istalgan foydalanuvchi)
- Barcha media uzatish (matn, rasm, video, ovoz, stiker...)
- Profil tahrirlash

### ⭐ Premium
- 👧 Qiz / 👦 Yigit alohida qidirish
- Muloqotchi profil ma'lumotlari (ism, yosh, viloyat)
- Ustuvor navbat

### 💳 Narxlar
| | Narx |
|--|--|
| 1 kun 🌟 | 5,000 UZS |
| 3 kun 💫 | 7,000 UZS |
| 1 hafta ⭐ | 15,000 UZS |
| 1 oy 👑 | 30,000 UZS |

---

## 🛠 Texnik stack

| | |
|--|--|
| Bot framework | aiogram 3.x |
| ORM | SQLAlchemy 2.x async |
| Driver | asyncpg |
| DB | PostgreSQL (Railway) |
| Migratsiya | Alembic |
| Python | 3.10+ |
