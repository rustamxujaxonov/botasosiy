"""
database.py — SQLAlchemy 2.x async ORM
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Integer,
    String, Text, select, update, delete, and_, or_, func, text
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
    pool_pre_ping=True,
    pool_recycle=300,
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

    id                = Column(BigInteger, primary_key=True)
    username          = Column(String(64), nullable=True)
    full_name         = Column(String(128), nullable=True)
    gender            = Column(String(10), nullable=True)
    display_name      = Column(String(32), nullable=True)
    age               = Column(Integer, nullable=True)
    region            = Column(String(64), nullable=True)
    registered        = Column(Boolean, default=False)
    referrer_id       = Column(BigInteger, nullable=True)
    ref_count         = Column(Integer, default=0)
    ref_premium_given = Column(Boolean, default=False)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
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
    gender      = Column(String(10), nullable=False)
    search_type = Column(String(10), nullable=False)
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

    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(BigInteger, nullable=False, index=True)
    plan             = Column(String(32), nullable=False)
    photo_file_id    = Column(String(256), nullable=False)
    message_id       = Column(Integer, nullable=True)
    admin_message_id = Column(Integer, nullable=True)
    status           = Column(String(20), default="pending")
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Referral(Base):
    __tablename__ = "referrals"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    inviter_id = Column(BigInteger, nullable=False, index=True)
    invitee_id = Column(BigInteger, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ============================================================
# DB INIT
# ============================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_premium_given BOOLEAN DEFAULT FALSE",
        ]
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception as e:
                logger.warning(f"Migration: {e}")
    logger.info("✅ Ma'lumotlar bazasi tayyor!")

# ============================================================
# USER
# ============================================================

async def create_or_update_user(user_id: int, username: str = None,
                                 full_name: str = None, referrer_id: int = None):
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
                registered=False,
                referrer_id=referrer_id,
                ref_count=0,
                ref_premium_given=False,
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
            "id":           user.id,
            "username":     user.username,
            "full_name":    user.full_name,
            "gender":       user.gender,
            "display_name": user.display_name,
            "age":          user.age,
            "region":       user.region,
            "registered":   user.registered,
            "referrer_id":  user.referrer_id,
            "ref_count":    user.ref_count,
        }

async def complete_registration(user_id: int, gender: str, display_name: str,
                                 age: int, region: str):
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
        return {"plan": prem.plan, "expires_at": prem.expires_at.isoformat()}

async def grant_premium(user_id: int, plan: str, days: int, admin_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Premium).where(
                Premium.user_id == user_id,
                Premium.expires_at > datetime.now(timezone.utc)
            ).order_by(Premium.expires_at.desc())
        )
        existing = result.scalar_one_or_none()
        base = existing.expires_at if existing else datetime.now(timezone.utc)
        new_expires = base + timedelta(days=days)
        session.add(Premium(
            user_id=user_id, plan=plan, granted_by=admin_id, expires_at=new_expires,
        ))
        await session.commit()

# ============================================================
# REFERRAL
# ============================================================

async def add_referral(inviter_id: int, invitee_id: int) -> bool:
    if inviter_id == invitee_id:
        return False
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Referral).where(Referral.invitee_id == invitee_id)
        )
        if result.scalar_one_or_none():
            return False
        session.add(Referral(inviter_id=inviter_id, invitee_id=invitee_id))
        await session.commit()
        return True

async def get_referral_count(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Referral.id)).where(Referral.inviter_id == user_id)
        )
        return result.scalar() or 0

async def get_referral_stats(user_id: int) -> dict:
    count = await get_referral_count(user_id)
    next_in = 5 - (count % 5) if count % 5 != 0 else 5
    return {
        "ref_count":             count,
        "next_premium_in":       next_in,
        "total_premiums_earned": count // 5,
    }

async def check_and_grant_referral_premium(user_id: int, bot) -> bool:
    count = await get_referral_count(user_id)
    if count == 0 or count % 5 != 0:
        return False

    milestone = count // 5

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Premium).where(
                Premium.user_id == user_id,
                Premium.plan == f"referral_{milestone}"
            )
        )
        if result.scalar_one_or_none():
            return False

    await grant_premium(user_id=user_id, plan=f"referral_{milestone}", days=1, admin_id=0)

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Tabriklaymiz!</b>\n\n"
                f"Siz <b>{count} ta</b> do'stni taklif qildingiz!\n"
                "🎁 <b>1 kunlik premium</b> hisobingizga qo'shildi!\n\n"
                "Endi jins bo'yicha qidirishdan foydalana olasiz 👍"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    return True

# ============================================================
# SEARCH QUEUE
# ============================================================

async def add_to_queue(user_id: int, gender: str, search_type: str):
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
            session.add(SearchQueue(user_id=user_id, gender=gender, search_type=search_type))
        await session.commit()

async def remove_from_queue(user_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(SearchQueue).where(SearchQueue.user_id == user_id))
        await session.commit()

async def is_in_queue(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SearchQueue.id).where(SearchQueue.user_id == user_id)
        )
        return result.scalar_one_or_none() is not None

async def get_queue_size() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(SearchQueue.id)))
        return result.scalar() or 0

async def find_match(user_id: int, my_gender: str, search_type: str) -> Optional[int]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            me = await session.execute(
                select(SearchQueue)
                .where(SearchQueue.user_id == user_id)
                .with_for_update(skip_locked=True)
            )
            if not me.scalar_one_or_none():
                return None

            conditions = [SearchQueue.user_id != user_id]
            if search_type == "female":
                conditions.append(SearchQueue.gender == "female")
            elif search_type == "male":
                conditions.append(SearchQueue.gender == "male")
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
                .order_by(SearchQueue.joined_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            partner_row = result.scalar_one_or_none()
            if not partner_row:
                return None

            partner_id = partner_row.user_id
            await session.execute(
                delete(SearchQueue).where(SearchQueue.user_id.in_([user_id, partner_id]))
            )
            session.add(Chat(user1_id=user_id, user2_id=partner_id, active=True))
            return partner_id

# ============================================================
# CHAT
# ============================================================

async def create_chat(user1_id: int, user2_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat).where(
                Chat.active == True,
                or_(
                    Chat.user1_id == user1_id, Chat.user2_id == user1_id,
                    Chat.user1_id == user2_id, Chat.user2_id == user2_id,
                )
            )
        )
        if result.scalar_one_or_none():
            return
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
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Chat)
            .where(Chat.active == True,
                   or_(Chat.user1_id == user_id, Chat.user2_id == user_id))
            .values(active=False, ended_at=datetime.now(timezone.utc))
        )
        await session.commit()

# ============================================================
# PAYMENT
# ============================================================

async def create_payment_request(user_id: int, plan: str,
                                  photo_file_id: str, message_id: int) -> int:
    async with AsyncSessionLocal() as session:
        req = PaymentRequest(
            user_id=user_id, plan=plan,
            photo_file_id=photo_file_id, message_id=message_id, status="pending"
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
            "id": req.id, "user_id": req.user_id,
            "plan": req.plan, "photo_file_id": req.photo_file_id, "status": req.status,
        }

async def update_payment_status(request_id: int, status: str, admin_message_id: int = None):
    async with AsyncSessionLocal() as session:
        values = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if admin_message_id:
            values["admin_message_id"] = admin_message_id
        await session.execute(
            update(PaymentRequest).where(PaymentRequest.id == request_id).values(**values)
        )
        await session.commit()
