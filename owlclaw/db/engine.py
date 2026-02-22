"""Async engine creation and lifecycle for OwlClaw."""

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from owlclaw.db.exceptions import ConfigurationError

_engines: dict[str, AsyncEngine] = {}



def _normalize_url(url: str) -> str:
    """Ensure URL uses postgresql+asyncpg driver."""
    u = url.strip()
    if u.startswith("postgresql://"):
        return "postgresql+asyncpg://" + u[len("postgresql://") :]
    if u.startswith("postgresql+asyncpg://"):
        return u
    raise ConfigurationError(
        "Database URL must be PostgreSQL (postgresql:// or postgresql+asyncpg://)."
    )


def _get_url(database_url: str | None) -> str:
    """Resolve database URL from argument or environment."""
    if database_url is not None and database_url != "":
        return _normalize_url(database_url)
    url = os.environ.get("OWLCLAW_DATABASE_URL")
    if not url or not url.strip():
        raise ConfigurationError(
            "Database URL not set. Set OWLCLAW_DATABASE_URL or pass database_url."
        )
    return _normalize_url(url)


def create_engine(
    database_url: str | None = None,
    *,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 1800,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async database engine.

    Args:
        database_url: PostgreSQL URL (postgresql+asyncpg://...).
            If None, uses OWLCLAW_DATABASE_URL.
        pool_size: Connection pool size.
        max_overflow: Extra connections beyond pool_size when busy.
        pool_timeout: Seconds to wait for a connection.
        pool_recycle: Seconds after which connections are recycled.
        pool_pre_ping: Ping connections before use.
        echo: Log SQL (for development).

    Returns:
        Configured AsyncEngine.

    Raises:
        ConfigurationError: URL missing or invalid.
    """
    url = _get_url(database_url)
    return create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
        echo=echo,
    )


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Get or create a cached engine for the given URL.

    Same URL returns the same engine instance.

    Args:
        database_url: Optional URL; if None, uses OWLCLAW_DATABASE_URL.

    Returns:
        AsyncEngine instance.

    Raises:
        ConfigurationError: URL missing or invalid.
    """
    url = _get_url(database_url)
    if url not in _engines:
        _engines[url] = create_engine(url)
    return _engines[url]


async def dispose_engine(database_url: str | None = None) -> None:
    """Dispose engine and close all connections.

    Args:
        database_url: Which engine to dispose; if None, disposes all.
    """
    if database_url is None:
        for key in list(_engines.keys()):
            await _engines[key].dispose()
            del _engines[key]
        return
    url = _get_url(database_url)
    if url in _engines:
        await _engines[url].dispose()
        del _engines[url]
