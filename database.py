"""
database.py — SQLAlchemy 2.x async ORM + PostgreSQL
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, String, Text, func, select, delete, update
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# ─── Engine & Session ────────────────────────────────────────────────────────

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # uzilgan connectionni avval tekshir
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # commit dan keyin obyektlar hali o'qiladi
)


# ─── Base ────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    user_id:      Mapped[int]           = mapped_column(BigInteger, primary_key=True)
    username:     Mapped[Optional[str]] = mapped_column(String(64))
    full_name:    Mapped[Optional[str]] = mapped_column(String(128))
    gender:       Mapped[Optional[str]] = mapped_column(String(10))
    age:          Mapped[Optional[int]] = mapped_column(Integer)
    region:       Mapped[Optional[str]] = mapped_column(String(64))
    display_name: Mapped[Optional[str]] = mapped_column(String(32))
    registered:   Mapped[bool]          = mapped_column(Boolean, default=False)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True),
                                                         server_default=func.now())
    updated_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True),
                                                         server_default=func.now(),
                                                         onupdate=func.now())


class Premium(Base):
    __tablename__ = "premium"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]      = mapped_column(BigInteger, ForeignKey("users.user_id"),
                                                  unique=True, index=True)
    plan:       Mapped[str]      = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[int]      = mapped_column(BigInteger)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  server_default=func.now())


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:      Mapped[int]           = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)
    plan:         Mapped[str]           = mapped_column(String(16))
    status:       Mapped[str]           = mapped_column(String(16), default="pending")
    photo_file_id:Mapped[Optional[str]] = mapped_column(Text)
    message_id:   Mapped[Optional[int]] = mapped_column(Integer)
    admin_msg_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True),
                                                         server_default=func.now())


class SearchQueue(Base):
    __tablename__ = "search_queue"

    user_id:     Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"),
                                              primary_key=True)
    gender:      Mapped[str] = mapped_column(String(10))
    search_type: Mapped[str] = mapped_column(String(10), default="any")
    added_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   server_default=func.now())


class ActiveChat(Base):
    __tablename__ = "active_chats"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user1_id:   Mapped[int]      = mapped_column(BigInteger, index=True)
    user2_id:   Mapped[int]      = mapped_column(BigInteger, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  server_default=func.now())


# ─── Init ────────────────────────────────────────────────────────────────────

async def init_db():
    """Jadvallarni yaratish (Alembic ishlatmasangiz)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL jadvallar tayyor ✅")


# ─── Context manager ─────────────────────────────────────────────────────────

def get_session() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionLocal


# ═══════════════════════════════════════════════════════════════════════════════
# USER
# ═══════════════════════════════════════════════════════════════════════════════

async def get_user(user_id: int) -> Optional[User]:
    async with AsyncSessionLocal() as s:
        return await s.get(User, user_id)


async def user_exists(user_id: int) -> bool:
    user = await get_user(user_id)
    return user is not None and user.registered


async def create_or_update_user(user_id: int,
                                 username: Optional[str] = None,
                                 full_name: Optional[str] = None):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            user = await s.get(User, user_id)
            if user is None:
                user = User(user_id=user_id,
                            username=username,
                            full_name=full_name)
                s.add(user)
            else:
                user.username  = username
                user.full_name = full_name


async def complete_registration(user_id: int, gender: str, display_name: str,
                                 age: int, region: str):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            user = await s.get(User, user_id)
            if user:
                user.gender       = gender
                user.display_name = display_name
                user.age          = age
                user.region       = region
                user.registered   = True
                user.updated_at   = datetime.utcnow()


async def update_profile(user_id: int, **kwargs):
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.utcnow()
    async with AsyncSessionLocal() as s:
        async with s.begin():
            await s.execute(
                update(User).where(User.user_id == user_id).values(**kwargs)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM
# ═══════════════════════════════════════════════════════════════════════════════

async def is_premium(user_id: int) -> bool:
    async with AsyncSessionLocal() as s:
        prem = await s.get(Premium, user_id)   # unique user_id = PK emas, ammo unique
        # get() PK bo'yicha ishlaydi; bu yerda id PK, user_id unique
        # shuning uchun select ishlatamiz
        result = await s.execute(
            select(Premium).where(Premium.user_id == user_id)
        )
        prem = result.scalar_one_or_none()
        if not prem:
            return False
        # Timezone-aware solishtiruv
        expires = prem.expires_at
        if expires.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        else:
            now = datetime.utcnow()
        return expires > now


async def grant_premium(user_id: int, plan: str, days: int, admin_id: int):
    from datetime import timezone
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    async with AsyncSessionLocal() as s:
        async with s.begin():
            result = await s.execute(
                select(Premium).where(Premium.user_id == user_id)
            )
            prem = result.scalar_one_or_none()
            if prem:
                prem.plan       = plan
                prem.expires_at = expires_at
                prem.granted_by = admin_id
                prem.granted_at = datetime.now(timezone.utc)
            else:
                prem = Premium(user_id=user_id, plan=plan,
                               expires_at=expires_at, granted_by=admin_id)
                s.add(prem)


async def get_premium_info(user_id: int) -> Optional[Premium]:
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            select(Premium).where(Premium.user_id == user_id)
        )
        return result.scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════

async def create_payment_request(user_id: int, plan: str,
                                  photo_file_id: str, message_id: int) -> int:
    async with AsyncSessionLocal() as s:
        async with s.begin():
            req = PaymentRequest(user_id=user_id, plan=plan,
                                  photo_file_id=photo_file_id,
                                  message_id=message_id)
            s.add(req)
        await s.refresh(req)
        return req.id


async def get_payment_request(request_id: int) -> Optional[PaymentRequest]:
    async with AsyncSessionLocal() as s:
        return await s.get(PaymentRequest, request_id)


async def update_payment_status(request_id: int, status: str,
                                 admin_msg_id: Optional[int] = None):
    values = {"status": status}
    if admin_msg_id is not None:
        values["admin_msg_id"] = admin_msg_id
    async with AsyncSessionLocal() as s:
        async with s.begin():
            await s.execute(
                update(PaymentRequest)
                .where(PaymentRequest.id == request_id)
                .values(**values)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

async def add_to_queue(user_id: int, user_gender: str, search_type: str = "any"):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            existing = await s.get(SearchQueue, user_id)
            if existing:
                existing.gender      = user_gender
                existing.search_type = search_type
                existing.added_at    = datetime.utcnow()
            else:
                s.add(SearchQueue(user_id=user_id,
                                   gender=user_gender,
                                   search_type=search_type))


async def remove_from_queue(user_id: int):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            await s.execute(
                delete(SearchQueue).where(SearchQueue.user_id == user_id)
            )


async def is_in_queue(user_id: int) -> bool:
    async with AsyncSessionLocal() as s:
        q = await s.get(SearchQueue, user_id)
        return q is not None


async def find_match(user_id: int, user_gender: str,
                     search_type: str = "any") -> Optional[int]:
    async with AsyncSessionLocal() as s:
        stmt = (
            select(SearchQueue.user_id)
            .where(SearchQueue.user_id != user_id)
            .order_by(SearchQueue.added_at)
            .limit(1)
        )
        if search_type == "female":
            stmt = stmt.where(SearchQueue.gender == "female")
        elif search_type == "male":
            stmt = stmt.where(SearchQueue.gender == "male")

        result = await s.execute(stmt)
        row = result.scalar_one_or_none()
        return row


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVE CHATS
# ═══════════════════════════════════════════════════════════════════════════════

async def create_chat(user1_id: int, user2_id: int) -> int:
    async with AsyncSessionLocal() as s:
        async with s.begin():
            chat = ActiveChat(user1_id=user1_id, user2_id=user2_id)
            s.add(chat)
        await s.refresh(chat)
        return chat.id


async def get_chat_partner(user_id: int) -> Optional[int]:
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            select(ActiveChat).where(
                (ActiveChat.user1_id == user_id) |
                (ActiveChat.user2_id == user_id)
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return None
        return chat.user2_id if chat.user1_id == user_id else chat.user1_id


async def end_chat(user_id: int):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            await s.execute(
                delete(ActiveChat).where(
                    (ActiveChat.user1_id == user_id) |
                    (ActiveChat.user2_id == user_id)
                )
            )


async def is_in_chat(user_id: int) -> bool:
    partner = await get_chat_partner(user_id)
    return partner is not None
