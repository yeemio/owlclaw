"""Async session factory and context manager for OwlClaw."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from owlclaw.db.engine import get_engine


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the engine.

    Args:
        engine: Async database engine.

    Returns:
        async_sessionmaker instance.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_session(
    engine: AsyncEngine | None = None,
) -> AsyncIterator[AsyncSession]:
    """Async context manager for a database session.

    Commits on success, rolls back on exception, closes on exit.

    Args:
        engine: Optional engine; if None, uses default from get_engine().

    Yields:
        AsyncSession instance.
    """
    if engine is None:
        engine = get_engine()
    factory = create_session_factory(engine)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
