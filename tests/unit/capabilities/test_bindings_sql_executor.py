from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.capabilities.bindings import SQLBindingConfig, SQLBindingExecutor


def _session_factory_with_result(result: Any) -> tuple[MagicMock, AsyncMock]:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    session_factory = MagicMock(return_value=session_cm)
    return session_factory, session


@pytest.mark.asyncio
async def test_sql_executor_select_query_returns_rows() -> None:
    result = MagicMock()
    result.keys.return_value = ["id", "name"]
    result.fetchall.return_value = [(1, "Alice"), (2, "Bob")]

    session_factory, session = _session_factory_with_result(result)
    executor = SQLBindingExecutor(session_factory_builder=lambda _: session_factory)
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="SELECT id, name FROM users WHERE id = :user_id",
    )

    payload = await executor.execute(config, {"user_id": 1})
    assert payload["status"] == "ok"
    assert payload["row_count"] == 2
    assert payload["data"][0]["id"] == 1
    assert payload["truncated"] is False
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_sql_executor_select_honors_max_rows_limit() -> None:
    result = MagicMock()
    result.keys.return_value = ["id"]
    result.fetchall.return_value = [(1,), (2,), (3,)]

    session_factory, _session = _session_factory_with_result(result)
    executor = SQLBindingExecutor(session_factory_builder=lambda _: session_factory)
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="SELECT id FROM users WHERE tenant = :tenant",
        max_rows=2,
    )

    payload = await executor.execute(config, {"tenant": "t1"})
    assert payload["row_count"] == 2
    assert payload["truncated"] is True


@pytest.mark.asyncio
async def test_sql_executor_write_query_commits_and_returns_affected_rows() -> None:
    result = MagicMock()
    result.rowcount = 3

    session_factory, session = _session_factory_with_result(result)
    executor = SQLBindingExecutor(session_factory_builder=lambda _: session_factory)
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="UPDATE users SET active = :active WHERE id = :user_id",
        read_only=False,
    )

    payload = await executor.execute(config, {"user_id": 7, "active": True})
    assert payload["affected_rows"] == 3
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sql_executor_read_only_blocks_write_queries() -> None:
    executor = SQLBindingExecutor()
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="UPDATE users SET active = :active WHERE id = :id",
        read_only=True,
    )
    with pytest.raises(PermissionError, match="read-only"):
        await executor.execute(config, {"id": 1, "active": True})


@pytest.mark.asyncio
async def test_sql_executor_shadow_mode_skips_write_execution() -> None:
    builder_called = {"value": False}

    def _builder(_: str) -> Any:
        builder_called["value"] = True
        return MagicMock()

    executor = SQLBindingExecutor(session_factory_builder=_builder)
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="UPDATE users SET active = :active WHERE id = :id",
        read_only=False,
        mode="shadow",
    )
    payload = await executor.execute(config, {"id": 1, "active": False})
    assert payload["status"] == "shadow"
    assert payload["executed"] is False
    assert builder_called["value"] is False


@pytest.mark.asyncio
async def test_sql_executor_rejects_string_interpolation_patterns() -> None:
    executor = SQLBindingExecutor()
    config = SQLBindingConfig(
        connection="sqlite+aiosqlite:///:memory:",
        query="SELECT * FROM users WHERE id = %s",
    )
    with pytest.raises(ValueError, match="parameterized placeholders"):
        await executor.execute(config, {"id": 1})
