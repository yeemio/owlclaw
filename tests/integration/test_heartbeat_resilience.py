"""Heartbeat resilience SLO checks for Decision 14 (D14-3)."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

import pytest

from owlclaw.agent.runtime.heartbeat import HeartbeatChecker

pytestmark = pytest.mark.integration


class _Result:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _Session:
    def __init__(self, values: list[Any], delay_seconds: float = 0.0) -> None:
        self._values = values
        self._delay_seconds = delay_seconds
        self._index = 0

    async def execute(self, _stmt: Any) -> _Result:
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        value = self._values[self._index] if self._index < len(self._values) else None
        self._index += 1
        return _Result(value)


class _SessionFactory:
    def __init__(self, session: _Session) -> None:
        self._session = session

    def __call__(self) -> Any:
        session = self._session

        class _CM:
            async def __aenter__(self_nonlocal) -> _Session:  # noqa: ANN001
                return session

            async def __aexit__(self_nonlocal, exc_type, exc, tb) -> None:  # noqa: ANN001
                return None

        return _CM()


def _checker_with_values(values: list[Any], *, delay_seconds: float = 0.0) -> HeartbeatChecker:
    session = _Session(values=values, delay_seconds=delay_seconds)
    return HeartbeatChecker(
        agent_id="resilience-agent",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(session),
            "database_pending_statuses": ["pending"],
            "database_query_timeout_seconds": 0.5,
        },
    )


@pytest.mark.asyncio
async def test_d14_heartbeat_miss_rate_under_five_percent() -> None:
    checker = _checker_with_values(["row"] * 100)
    detected = 0
    for _ in range(100):
        if await checker.check_events("tenant-slo"):
            detected += 1
    misses = 100 - detected
    assert misses <= 5


@pytest.mark.asyncio
async def test_d14_heartbeat_latency_under_500ms() -> None:
    checker = _checker_with_values([None], delay_seconds=0.01)
    started = perf_counter()
    await checker.check_events("tenant-slo")
    elapsed_ms = (perf_counter() - started) * 1000
    assert elapsed_ms < 500


@pytest.mark.asyncio
async def test_d14_heartbeat_false_positive_rate_under_one_percent() -> None:
    checker = _checker_with_values([None] * 100)
    false_positives = 0
    for _ in range(100):
        if await checker.check_events("tenant-slo"):
            false_positives += 1
    assert false_positives <= 1
