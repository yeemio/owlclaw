"""Event aggregation for db change trigger."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from owlclaw.triggers.db_change.adapter import DBChangeEvent

AggregationMode = Literal["passthrough", "debounce", "batch", "hybrid"]


class EventAggregator:
    """Aggregate db change events by debounce/batch/hybrid strategy."""

    def __init__(
        self,
        *,
        mode: AggregationMode,
        on_flush: Callable[[list[DBChangeEvent]], Awaitable[None]],
        debounce_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> None:
        self._mode = mode
        self._on_flush = on_flush
        self._debounce_seconds = debounce_seconds
        self._batch_size = batch_size
        self._buffer: list[DBChangeEvent] = []
        self._debounce_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def push(self, event: DBChangeEvent) -> None:
        async with self._lock:
            self._buffer.append(event)
            if self._mode == "passthrough":
                await self._flush_locked()
                return
            if self._mode in {"batch", "hybrid"} and self._batch_size and len(self._buffer) >= self._batch_size:
                await self._flush_locked()
                return
            if self._mode in {"debounce", "hybrid"} and self._debounce_seconds is not None:
                self._reset_debounce_task()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    def _reset_debounce_task(self) -> None:
        if self._debounce_task is not None:
            self._debounce_task.cancel()
        self._debounce_task = asyncio.create_task(self._debounce_wait_then_flush())

    async def _debounce_wait_then_flush(self) -> None:
        try:
            await asyncio.sleep(self._debounce_seconds or 0)
        except asyncio.CancelledError:
            return
        await self.flush()

    async def _flush_locked(self) -> None:
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()
        if self._debounce_task is not None:
            self._debounce_task.cancel()
            self._debounce_task = None
        await self._on_flush(batch)
