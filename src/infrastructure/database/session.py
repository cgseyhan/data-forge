import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# DATABASE_URL env variable'ı asyncpg driver'ı ile kullanılmalı.
# Örnek: postgresql+asyncpg://user:password@localhost:5432/dataforge
# Test için SQLite: sqlite+aiosqlite:///./dataforge_test.db
_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./dataforge_dev.db"
)

# SQLite için check_same_thread=False gerekli; PostgreSQL'de bu arg yok.
_connect_args = {}
if _DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a DB session and handles
    commit/rollback/close lifecycle automatically.

    Usage:
        async with get_session() as session:
            session.add(record)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Creates all tables if they don't exist yet.
    For production use Alembic migrations instead.
    """
    from src.infrastructure.database.models import Base  # noqa: F401 — import triggers metadata registration
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized (create_all).")
