"""Property tests for owlclaw.db engine management."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.db import ConfigurationError
from owlclaw.db import engine as db_engine


def _build_postgres_url(db_name: str) -> str:
    safe_db = "".join(ch for ch in db_name if ch.isalnum() or ch in ("_", "-")) or "db"
    return f"postgresql://user:pass@localhost/{safe_db}"


@given(
    st.text(min_size=1, max_size=24).filter(
        lambda s: not s.startswith("postgresql://") and not s.startswith("postgresql+asyncpg://")
    )
)
def test_property_database_url_format_validation(invalid_url: str) -> None:
    """Property: non-PostgreSQL URL schemes are rejected."""
    with pytest.raises(ConfigurationError):
        db_engine._normalize_url(invalid_url)  # noqa: SLF001


@given(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=20))
def test_property_get_engine_reuses_cached_instance(name_a: str, name_b: str) -> None:
    """Property: same normalized URL returns the same cached engine instance."""
    url_a = _build_postgres_url(name_a)
    url_b = _build_postgres_url(name_b)

    db_engine._engines.clear()  # noqa: SLF001
    created: dict[str, object] = {}

    def fake_create_engine(database_url: str | None = None, **_: Any) -> object:
        assert database_url is not None
        normalized = db_engine._normalize_url(database_url)  # noqa: SLF001
        engine_obj = created.get(normalized)
        if engine_obj is None:
            engine_obj = object()
            created[normalized] = engine_obj
        return engine_obj

    original = db_engine.create_engine
    db_engine.create_engine = fake_create_engine  # type: ignore[assignment]
    try:
        first = db_engine.get_engine(url_a)
        second = db_engine.get_engine(url_a)
        assert first is second

        third = db_engine.get_engine(url_b)
        if db_engine._normalize_url(url_a) == db_engine._normalize_url(url_b):  # noqa: SLF001
            assert third is first
        else:
            assert third is not first
    finally:
        db_engine.create_engine = original  # type: ignore[assignment]
        db_engine._engines.clear()  # noqa: SLF001


@given(
    st.sampled_from(
        [
            "mysql://user:pass@localhost/db",
            "sqlite:///tmp.db",
            "mssql://user:pass@localhost/db",
            "oracle://user:pass@localhost/db",
        ]
    )
)
def test_property_unsupported_dialect_raises_error(url: str) -> None:
    """Property: unsupported database dialects raise ConfigurationError."""
    with pytest.raises(ConfigurationError):
        db_engine._normalize_url(url)  # noqa: SLF001


@given(
    pool_size=st.integers(min_value=1, max_value=100),
    max_overflow=st.integers(min_value=0, max_value=100),
    pool_timeout=st.floats(min_value=0.1, max_value=120.0, allow_nan=False, allow_infinity=False),
    pool_recycle=st.integers(min_value=1, max_value=7200),
    pool_pre_ping=st.booleans(),
    echo=st.booleans(),
)
def test_property_pool_parameters_forwarded_to_sqlalchemy(
    pool_size: int,
    max_overflow: int,
    pool_timeout: float,
    pool_recycle: int,
    pool_pre_ping: bool,
    echo: bool,
) -> None:
    """Property: pool settings are passed through to create_async_engine."""
    captured: dict[str, Any] = {}

    def fake_create_async_engine(url: str, **kwargs: Any) -> object:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    original = db_engine.create_async_engine
    db_engine.create_async_engine = fake_create_async_engine  # type: ignore[assignment]
    try:
        db_engine.create_engine(
            "postgresql://user:pass@localhost/propdb",
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            echo=echo,
        )
    finally:
        db_engine.create_async_engine = original  # type: ignore[assignment]

    assert captured["url"].startswith("postgresql+asyncpg://")
    assert captured["kwargs"]["pool_size"] == pool_size
    assert captured["kwargs"]["max_overflow"] == max_overflow
    assert captured["kwargs"]["pool_timeout"] == pool_timeout
    assert captured["kwargs"]["pool_recycle"] == pool_recycle
    assert captured["kwargs"]["pool_pre_ping"] == pool_pre_ping
    assert captured["kwargs"]["echo"] == echo
