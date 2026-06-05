"""
database.py — SQLAlchemy 2.x async ORM
Barcha muammolar tuzatildi:
- Chat jadvalida to'liq CRUD
- Queue race condition himoyasi (SELECT FOR UPDATE)
- Premium muddati tekshiruvi avtomatik
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Integer,
    String, Text, select, update, delete, and_, or_
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # Railway disconnect'dan himoya
    pool_recycle=300,             # 5 daqiqada ulanishni yangilash
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# ============================================================
# MODELS
# ============================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id           = Column(BigInteger, primary_key=True)   # Telegram user_id
    username     = Column(String(64), nullable=True)
    full_name    = Column(String(128), nullable=True)
    gender       = Column(String(10), nullable=True)
    display_name = Column(String(32), nullable=True)
    age          = Column(Integer, nullable=True)
    region       = Column(String(64), nullable=True)
    registered   = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))


class Premium(Base):
    __tablename__ = "premiums"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, nullable=False, index=True)
    plan       = Column(String(32), nullable=False)
    granted_by = Column(BigInteger, nullable=True)
    granted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)


class SearchQueue(Base):
    __tablename__ = "search_queue"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(BigInteger, nullable=False, unique=True, index=True)
    gender      = Column(String(10), nullable=False)   # user's own gender
    search_type = Column(String(10), nullable=False)   # 'any' | 'male' | 'female'
    joined_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Chat(Base):
    __tablename__ = "chats"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user1_id   = Column(BigInteger, nullable=False, index=True)
    user2_id   = Column(BigInteger, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at   = Column(DateTime(timezone=True), nullable=True)
    active     = Column(Boolean, default=True)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(BigInteger, nullable=False, index=True)
    plan            = Column(String(32), nullable=False)
    photo_file_id   = Column(String(256), nullable=False)
    message_id      = Column(Integer, nullable=True)
    admin_message_id= Column(Integer, nullable=True)
    status          = Column(String(20), default="pending")  # pending | approved | rejected
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ============================================================
# DB INIT
# ============================================================

async def init_db():
    async with engine.begin() as conn:
        # Eski search_queue ni o'chirib, yangisini yaratish (eng ishonchli)
        await conn.run_sync(lambda s: s.execute("DROP TABLE IF EXISTS search_queue CASCADE"))
        
        # Barcha jadvallarni yaratish
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("✅ Ma'lumotlar bazasi tozalab qayta yaratildi!")
# ============================================================
# USER
# ============================================================

async def create_or_update_user(user_id: int, username: str = None, full_name: str = None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            if username is not None:
                user.username = username
            if full_name is not None:
                user.full_name = full_name
            user.updated_at = datetime.now(timezone.utc)
        else:
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                registered=False
            )
            session.add(user)

        await session.commit()


async def user_exists(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user_id, User.registered == True)
        )
        return result.scalar_one_or_none() is not None


async def get_user(user_id: int) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "gender": user.gender,
            "display_name": user.display_name,
            "age": user.age,
            "region": user.region,
            "registered": user.registered,
        }


async def complete_registration(
    user_id: int,
    gender: str,
    display_name: str,
    age: int,
    region: str
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.gender       = gender
            user.display_name = display_name
            user.age          = age
            user.region       = region
            user.registered   = True
            user.updated_at   = datetime.now(timezone.utc)
            await session.commit()


async def update_profile(user_id: int, **kwargs):
    """gender, display_name, age, region dan istalganini yangilash"""
    allowed = {"gender", "display_name", "age", "region"}
    data = {k: v for k, v in kwargs.items() if k in allowed}
    if not data:
        return
    data["updated_at"] = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(**data)
        )
        await session.commit()


# ============================================================
# PREMIUM
# ============================================================

async def is_premium(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Premium).where(
                Premium.user_id == user_id,
                Premium.expires_at > datetime.now(timezone.utc)
            )
        )
        return result.scalar_one_or_none() is not None


async def get_premium_info(user_id: int) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Premium).where(
                Premium.user_id == user_id,
                Premium.expires_at > datetime.now(timezone.utc)
            ).order_by(Premium.expires_at.desc())
        )
        prem = result.scalar_one_or_none()
        if not prem:
            return None
        return {
            "plan": prem.plan,
            "expires_at": prem.expires_at.isoformat(),
        }


async def grant_premium(user_id: int, plan: str, days: int, admin_id: int):
    async with AsyncSessionLocal() as session:
        # Eski premium bormi? Uning ustiga qo'shamiz
        result = await session.execute(
            select(Premium).where(
                Premium.user_id == user_id,
                Premium.expires_at > datetime.now(timezone.utc)
            ).order_by(Premium.expires_at.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            base = existing.expires_at
        else:
            base = datetime.now(timezone.utc)

        new_expires = base + timedelta(days=days)

        prem = Premium(
            user_id=user_id,
            plan=plan,
            granted_by=admin_id,
            expires_at=new_expires,
        )
        session.add(prem)
        await session.commit()


# ============================================================
# SEARCH QUEUE
# ============================================================

async def add_to_queue(user_id: int, gender: str, search_type: str):
    """Navbatga qo'shish — allaqachon borsa yangilash"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SearchQueue).where(SearchQueue.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.gender      = gender
            existing.search_type = search_type
            existing.joined_at   = datetime.now(timezone.utc)
        else:
            session.add(SearchQueue(
                user_id=user_id,
                gender=gender,
                search_type=search_type,
            ))
        await session.commit()


async def remove_from_queue(user_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(SearchQueue).where(SearchQueue.user_id == user_id)
        )
        await session.commit()


async def is_in_queue(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SearchQueue.id).where(SearchQueue.user_id == user_id)
        )
        return result.scalar_one_or_none() is not None


async def find_match(user_id: int, my_gender: str, search_type: str) -> Optional[int]:
    """
    Mos juftlikni topish.
    Muammo: A B ni topdi, B ham A ni topishi mumkin → ikki chat ochiladi.
    Yechim: SELECT FOR UPDATE WITH SKIP LOCKED ishlatamiz.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Mening holatim hali navbatdami?
            me = await session.execute(
                select(SearchQueue)
                .where(SearchQueue.user_id == user_id)
                .with_for_update(skip_locked=True)
            )
            me_row = me.scalar_one_or_none()
            if not me_row:
                return None  # allaqachon olib tashlangan

            # Mos sheriklarni qidirish
            # search_type='any' → istalgan jins
            # search_type='male' → erkak qidirmoqda
            # search_type='female' → ayol qidirmoqda
            conditions = [
                SearchQueue.user_id != user_id,
            ]

            # Men qanday qidiraman?
            if search_type == "female":
                conditions.append(SearchQueue.gender == "female")
            elif search_type == "male":
                conditions.append(SearchQueue.gender == "male")

            # Sherik meni qabul qiladimi?
            # Sherik 'any' qidirsa → har kimni qabul qiladi
            # Sherik 'female' qidirsa → men female bo'lishim kerak
            # Sherik 'male' qidirsa → men male bo'lishim kerak
            conditions.append(
                or_(
                    SearchQueue.search_type == "any",
                    and_(SearchQueue.search_type == "female", my_gender == "female"),
                    and_(SearchQueue.search_type == "male",   my_gender == "male"),
                )
            )

            result = await session.execute(
                select(SearchQueue)
                .where(and_(*conditions))
                .order_by(SearchQueue.joined_at)   # birinchi kirgan birinchi chiqadi
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            partner_row = result.scalar_one_or_none()
            if not partner_row:
                return None

            partner_id = partner_row.user_id

            # Ikkalasini navbatdan olib tashlash (transaction ichida)
            await session.execute(
                delete(SearchQueue).where(
                    SearchQueue.user_id.in_([user_id, partner_id])
                )
            )
            # Chat yaratish ham shu transaction ichida
            session.add(Chat(user1_id=user_id, user2_id=partner_id, active=True))

        return partner_id


# ============================================================
# CHAT
# ============================================================

async def create_chat(user1_id: int, user2_id: int):
    """
    find_match allaqachon chat yaratadi.
    Bu funksiya faqat zapas holat uchun (eski kod bilan moslik).
    """
    async with AsyncSessionLocal() as session:
        # Ikkalasi uchun faol chat bormi?
        result = await session.execute(
            select(Chat).where(
                Chat.active == True,
                or_(
                    Chat.user1_id == user1_id,
                    Chat.user2_id == user1_id,
                    Chat.user1_id == user2_id,
                    Chat.user2_id == user2_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return  # allaqachon bor

        session.add(Chat(user1_id=user1_id, user2_id=user2_id, active=True))
        await session.commit()


async def is_in_chat(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat.id).where(
                Chat.active == True,
                or_(Chat.user1_id == user_id, Chat.user2_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None


async def get_chat_partner(user_id: int) -> Optional[int]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat).where(
                Chat.active == True,
                or_(Chat.user1_id == user_id, Chat.user2_id == user_id)
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return None
        return chat.user2_id if chat.user1_id == user_id else chat.user1_id


async def end_chat(user_id: int):
    """Foydalanuvchi bilan bog'liq barcha faol chatlarni yopish"""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Chat)
            .where(
                Chat.active == True,
                or_(Chat.user1_id == user_id, Chat.user2_id == user_id)
            )
            .values(active=False, ended_at=datetime.now(timezone.utc))
        )
        await session.commit()


# ============================================================
# PAYMENT
# ============================================================

async def create_payment_request(
    user_id: int,
    plan: str,
    photo_file_id: str,
    message_id: int
) -> int:
    async with AsyncSessionLocal() as session:
        req = PaymentRequest(
            user_id=user_id,
            plan=plan,
            photo_file_id=photo_file_id,
            message_id=message_id,
            status="pending"
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        return req.id


async def get_payment_request(request_id: int) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PaymentRequest).where(PaymentRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if not req:
            return None
        return {
            "id": req.id,
            "user_id": req.user_id,
            "plan": req.plan,
            "photo_file_id": req.photo_file_id,
            "status": req.status,
        }


async def update_payment_status(request_id: int, status: str, admin_message_id: int = None):
    async with AsyncSessionLocal() as session:
        values = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if admin_message_id:
            values["admin_message_id"] = admin_message_id
        await session.execute(
            update(PaymentRequest)
            .where(PaymentRequest.id == request_id)
            .values(**values)
        )
        await session.commit()
