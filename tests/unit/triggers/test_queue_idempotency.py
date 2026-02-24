from __future__ import annotations

import asyncio
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.triggers.queue import MockIdempotencyStore, RedisIdempotencyStore


class _FakeRedisClient:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    async def set(self, key: str, value: Any, ex: int) -> None:
        self._data[key] = value

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)


@pytest.mark.asyncio
async def test_mock_idempotency_store_ttl_expiry() -> None:
    store = MockIdempotencyStore()
    await store.set("k-1", {"ok": True}, ttl=1)

    assert await store.exists("k-1") is True
    assert await store.get("k-1") == {"ok": True}

    await asyncio.sleep(1.1)

    assert await store.exists("k-1") is False
    assert await store.get("k-1") is None


@pytest.mark.asyncio
async def test_redis_idempotency_store_uses_prefix() -> None:
    client = _FakeRedisClient()
    store = RedisIdempotencyStore(client, key_prefix="idempotency:")

    await store.set("abc", {"done": 1}, ttl=10)

    assert await store.exists("abc") is True
    assert await store.get("abc") == {"done": 1}
    assert "idempotency:abc" in client._data


@given(
    key=st.text(min_size=1, max_size=32),
    value=st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=5),
)
def test_property_idempotency_guarantee(key: str, value: dict[str, int]) -> None:
    """Feature: triggers-queue, Property 15: 幂等性保证."""
    async def _run() -> None:
        store = MockIdempotencyStore()
        assert await store.exists(key) is False
        await store.set(key, value, ttl=60)
        assert await store.exists(key) is True
        assert await store.get(key) == value

    asyncio.run(_run())


@given(ttl=st.integers(min_value=1, max_value=2))
def test_property_idempotency_window(ttl: int) -> None:
    """Feature: triggers-queue, Property 16: 幂等性窗口期."""
    async def _run() -> None:
        store = MockIdempotencyStore()
        await store.set("window", "v", ttl=ttl)
        assert await store.exists("window") is True
        assert await store.get("window") == "v"

    asyncio.run(_run())
