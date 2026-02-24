"""Signal router for unified dispatch."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from owlclaw.triggers.signal.models import Signal, SignalResult, SignalType


class SignalHandler(Protocol):
    async def __call__(self, signal: Signal) -> SignalResult: ...


class SignalRouter:
    """Dispatch signal requests to registered handlers."""

    def __init__(self, handlers: dict[SignalType, Callable[[Signal], Awaitable[SignalResult]]]) -> None:
        self._handlers = handlers

    async def dispatch(self, signal: Signal) -> SignalResult:
        handler = self._handlers.get(signal.type)
        if handler is None:
            return SignalResult(status="error", error_code="bad_request", message="unsupported_signal")
        return await handler(signal)
