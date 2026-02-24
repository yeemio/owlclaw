"""Adapter interfaces and Postgres NOTIFY implementation for db change trigger."""

from __future__ import annotations

import asyncio
import contextlib
import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    import asyncpg
except Exception:  # pragma: no cover - runtime optional
    asyncpg = None  # type: ignore[assignment]


@dataclass(slots=True)
class DBChangeEvent:
    """One normalized db change event."""

    channel: str
    payload: dict[str, Any]
    timestamp: datetime
    source: str = "notify"


class DBChangeAdapter(ABC):
    """Abstract adapter for db change event sources."""

    @abstractmethod
    async def start(self, channels: list[str]) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def on_event(self, callback: Callable[[DBChangeEvent], Awaitable[None]]) -> None: ...


class PostgresNotifyAdapter(DBChangeAdapter):
    """PostgreSQL NOTIFY/LISTEN adapter based on asyncpg."""

    def __init__(self, dsn: str, reconnect_interval: float = 30.0) -> None:
        self._dsn = dsn
        self._reconnect_interval = reconnect_interval
        self._callbacks: list[Callable[[DBChangeEvent], Awaitable[None]]] = []
        self._conn: Any | None = None
        self._channels: list[str] = []
        self._running = False
        self._health_task: asyncio.Task[None] | None = None

    def on_event(self, callback: Callable[[DBChangeEvent], Awaitable[None]]) -> None:
        self._callbacks.append(callback)

    async def start(self, channels: list[str]) -> None:
        if asyncpg is None:  # pragma: no cover
            raise RuntimeError("asyncpg is required for PostgresNotifyAdapter")
        self._channels = list(dict.fromkeys(channels))
        self._conn = await asyncpg.connect(self._dsn)
        for channel in self._channels:
            await self._conn.add_listener(channel, self._on_notify)
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        self._running = False
        if self._health_task is not None:
            self._health_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_task
            self._health_task = None
        if self._conn is not None:
            for channel in self._channels:
                with contextlib.suppress(Exception):
                    await self._conn.remove_listener(channel, self._on_notify)
            await self._conn.close()
            self._conn = None

    async def _reconnect(self) -> None:
        if asyncpg is None:  # pragma: no cover
            return
        if self._conn is not None:
            with contextlib.suppress(Exception):
                await self._conn.close()
        self._conn = await asyncpg.connect(self._dsn)
        for channel in self._channels:
            await self._conn.add_listener(channel, self._on_notify)

    async def _health_check_loop(self) -> None:
        while self._running:
            try:
                if self._conn is None:
                    await self._reconnect()
                else:
                    await self._conn.execute("SELECT 1")
            except Exception:
                await self._reconnect()
            await asyncio.sleep(self._reconnect_interval)

    async def _on_notify(self, conn: Any, pid: int, channel: str, payload: str) -> None:  # noqa: ARG002
        try:
            parsed = json.loads(payload) if payload else {}
            if not isinstance(parsed, dict):
                parsed = {"value": parsed}
        except Exception:
            parsed = {"raw_payload": payload, "parse_error": True}
        event = DBChangeEvent(
            channel=channel,
            payload=parsed,
            timestamp=datetime.now(timezone.utc),
            source="notify",
        )
        for callback in self._callbacks:
            await callback(event)
