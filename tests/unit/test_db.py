"""Unit tests for owlclaw.db (database-core)."""

import os

import pytest

from owlclaw.db import (
    Base,
    ConfigurationError,
    create_engine,
    get_engine,
    get_session,
)


def test_base_has_metadata():
    """Base exposes metadata for Alembic."""
    assert Base.metadata is not None


def test_base_tenant_id_column():
    """Base has tenant_id mapped column."""
    assert hasattr(Base, "tenant_id")
    # Mapped column is on the class
    assert "tenant_id" in Base.__dict__ or hasattr(Base, "tenant_id")


def test_create_engine_requires_postgresql_url():
    """create_engine raises ConfigurationError for non-PostgreSQL URL."""
    with pytest.raises(ConfigurationError) as exc_info:
        create_engine("mysql://localhost/db")
    assert "PostgreSQL" in str(exc_info.value)


def test_get_engine_without_url_raises_when_env_unset(monkeypatch):
    """get_engine() raises ConfigurationError when OWLCLAW_DATABASE_URL not set."""
    monkeypatch.delenv("OWLCLAW_DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError) as exc_info:
        get_engine()
    assert "not set" in str(exc_info.value).lower() or "OWLCLAW" in str(exc_info.value)


def test_create_engine_normalizes_postgresql_to_asyncpg():
    """create_engine normalizes postgresql:// to postgresql+asyncpg://."""
    eng = create_engine("postgresql://u:p@localhost/db")
    assert eng.url.drivername == "postgresql+asyncpg"


def test_get_engine_caches_by_url():
    """get_engine returns same engine for same URL."""
    url = "postgresql://u:p@host/db1"
    os.environ["OWLCLAW_DATABASE_URL"] = url
    try:
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
    finally:
        os.environ.pop("OWLCLAW_DATABASE_URL", None)


def test_get_session_returns_async_context_manager():
    """get_session() returns an async context manager."""
    cm = get_session()
    assert hasattr(cm, "__aenter__") and hasattr(cm, "__aexit__")
