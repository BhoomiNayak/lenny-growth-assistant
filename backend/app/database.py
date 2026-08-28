"""Async SQLAlchemy database engine and session management.

Uses asyncpg as the async driver for PostgreSQL.
Provides a dependency for FastAPI route injection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session.

    Automatically commits on success, rolls back on exception,
    and closes the session when done.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Check if database is reachable. Used by health endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        return True
    except Exception:
        return False


async def wait_for_db(max_retries: int = 10, base_delay: float = 1.0) -> bool:
    """Wait for the database to become reachable with exponential backoff.

    Called on application startup so the API doesn't crash if the DB is
    still initializing (common in Docker Compose where services start in
    parallel). Returns True if connected, False if all retries exhausted.
    """
    import asyncio

    from app.utils.logging import get_logger

    logger = get_logger(__name__)

    for attempt in range(1, max_retries + 1):
        if await check_db_connection():
            logger.info("database.connected", attempt=attempt)
            return True

        # Exponential backoff capped at 15s
        delay = min(base_delay * (2 ** (attempt - 1)), 15.0)
        logger.warning(
            "database.connection_retry",
            attempt=attempt,
            max_retries=max_retries,
            retry_in_seconds=delay,
        )
        await asyncio.sleep(delay)

    logger.error("database.connection_failed", max_retries=max_retries)
    return False
