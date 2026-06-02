from datetime import datetime

from sqlalchemy import (
    BigInteger, Column, DateTime, Index, Integer, String, Text, TinyInteger,
    create_engine, select, text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, unique=True)
    tenant_name = Column(String(100), nullable=False)
    contact = Column(String(50))
    phone = Column(String(20))
    status = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)
    user_id = Column(String(100), nullable=False)
    channel = Column(String(32), nullable=False, default="wechat")
    nickname = Column(String(100))
    phone = Column(String(20))
    tags = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("uk_tenant_user", "tenant_id", "user_id", "channel", unique=True),
    )


class Product(Base):
    __tablename__ = "product"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)
    product_name = Column(String(200), nullable=False)
    gold_type = Column(String(50))
    diamond_size = Column(String(50))
    price_range = Column(String(100))
    inventory = Column(Integer, default=0)
    category = Column(String(50))
    status = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FAQ(Base):
    __tablename__ = "faq"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50))
    sort = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    file_type = Column(String(32))
    content = Column(Text)
    category = Column(String(50))
    status = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatLog(Base):
    __tablename__ = "chat_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)
    channel = Column(String(32), nullable=False, default="wechat")
    user_id = Column(String(100), nullable=False)
    session_id = Column(String(100), nullable=False)
    user_query = Column(Text)
    ai_answer = Column(Text)
    intent = Column(String(50), default="general")
    need_manual = Column(TinyInteger, default=0)
    manual_reason = Column(String(255))
    used_tokens = Column(Integer, default=0)
    review_status = Column(String(20), default="pending")  # pending/reviewed/flagged
    quality_score = Column(TinyInteger)  # 1-5, NULL=not reviewed
    reviewer_id = Column(BigInteger)
    review_comment = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class PromptConfig(Base):
    __tablename__ = "prompt_config"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, unique=True)
    system_prompt = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminUser(Base):
    __tablename__ = "admin_user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    tenant_id = Column(String(64))
    status = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db(mysql_url: str):
    global _engine, _session_factory
    _engine = create_async_engine(mysql_url, echo=False, pool_size=10, max_overflow=20)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def close_db():
    global _engine
    if _engine:
        await _engine.dispose()


def get_session() -> AsyncSession:
    return _session_factory()


def create_tables_sync(mysql_url: str):
    sync_url = mysql_url.replace("+aiomysql", "+pymysql")
    engine = create_engine(sync_url, echo=True)
    Base.metadata.create_all(engine)
    engine.dispose()


async def ensure_admin_user():
    """Create default admin user if not exists."""
    import bcrypt as _bcrypt

    async with get_session() as session:
        result = await session.execute(
            select(AdminUser).where(AdminUser.username == "admin")
        )
        if result.scalar_one_or_none():
            return
        hashed = _bcrypt.hashpw(b"admin123", _bcrypt.gensalt(12)).decode()
        admin = AdminUser(
            username="admin",
            password=hashed,
            role="super_admin",
        )
        session.add(admin)
        await session.commit()


async def check_mysql_health() -> dict:
    """Check MySQL connectivity. Returns {"status": "ok"/"error", "detail": ...}."""
    if _engine is None:
        return {"status": "error", "detail": "Database not initialized"}
    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
