"""Unit tests for HeartbeatChecker (agent-runtime Task 5.3)."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

import pytest

from owlclaw.agent.runtime.heartbeat import HeartbeatChecker


class TestHeartbeatCheckerNoEvents:
    """Test no-events scenarios (all sources return False in MVP)."""

    @pytest.mark.asyncio
    async def test_check_events_returns_false_by_default(self) -> None:
        """Default config: all sources return False, so no events."""
        checker = HeartbeatChecker(agent_id="bot")
        result = await checker.check_events()
        assert result is False

    def test_init_trims_agent_id_and_rejects_blank(self) -> None:
        checker = HeartbeatChecker(agent_id="  bot  ")
        assert checker.agent_id == "bot"
        with pytest.raises(ValueError, match="agent_id must be a non-empty string"):
            HeartbeatChecker(agent_id="   ")

    @pytest.mark.asyncio
    async def test_check_events_disabled_returns_false(self) -> None:
        """When disabled, always returns False (no events)."""
        checker = HeartbeatChecker(agent_id="bot", config={"enabled": False})
        result = await checker.check_events()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_events_string_false_disables_checker(self) -> None:
        checker = HeartbeatChecker(agent_id="bot", config={"enabled": "false"})
        result = await checker.check_events()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_events_custom_sources(self) -> None:
        """Custom event_sources still return False when unimplemented."""
        checker = HeartbeatChecker(
            agent_id="bot",
            config={"event_sources": ["webhook", "schedule"]},
        )
        result = await checker.check_events()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_events_empty_sources_returns_false(self) -> None:
        """Empty event_sources list => no checks, no events."""
        checker = HeartbeatChecker(
            agent_id="bot",
            config={"event_sources": []},
        )
        assert checker._event_sources == []
        result = await checker.check_events()
        assert result is False

    def test_normalize_event_sources_from_string(self) -> None:
        checker = HeartbeatChecker(agent_id="bot", config={"event_sources": "webhook"})
        assert checker._event_sources == ["webhook"]

    def test_normalize_event_sources_lowercases_values(self) -> None:
        checker = HeartbeatChecker(
            agent_id="bot",
            config={"event_sources": ["Webhook", "QUEUE", " schedule "]},
        )
        assert checker._event_sources == ["webhook", "queue", "schedule"]

    def test_normalize_event_sources_filters_unknown_values(self) -> None:
        checker = HeartbeatChecker(
            agent_id="bot",
            config={"event_sources": ["webhook", "unknown-source"]},
        )
        assert checker._event_sources == ["webhook"]

    def test_normalize_event_sources_invalid_type_uses_default(self) -> None:
        checker = HeartbeatChecker(agent_id="bot", config={"event_sources": 123})
        assert checker._event_sources == [
            "webhook",
            "queue",
            "database",
            "schedule",
            "external_api",
        ]

    def test_normalize_event_sources_supports_set_input(self) -> None:
        checker = HeartbeatChecker(
            agent_id="bot",
            config={"event_sources": {"WEBHOOK", "queue", "unknown"}},
        )
        assert set(checker._event_sources) == {"webhook", "queue"}


class TestHeartbeatCheckerWithEvents:
    """Test has-events scenario via subclass override."""

    @pytest.mark.asyncio
    async def test_check_events_returns_true_when_source_has_events(self) -> None:
        """When a source reports events, check_events returns True."""

        class CheckerWithWebhookEvents(HeartbeatChecker):
            async def _check_webhook_events(self) -> bool:
                return True

        checker = CheckerWithWebhookEvents(
            agent_id="bot",
            config={"event_sources": ["webhook", "queue"]},
        )
        result = await checker.check_events()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_events_external_api_source_supported(self) -> None:
        """external_api should be a valid event source branch."""

        class CheckerWithExternalApiEvents(HeartbeatChecker):
            async def _check_external_api_events(self) -> bool:
                return True

        checker = CheckerWithExternalApiEvents(
            agent_id="bot",
            config={"event_sources": ["external_api"]},
        )
        result = await checker.check_events()
        assert result is True


class _Result:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _Session:
    def __init__(self, value: Any, delay_seconds: float = 0.0) -> None:
        self._value = value
        self._delay_seconds = delay_seconds
        self.statements: list[Any] = []

    async def execute(self, stmt: Any) -> _Result:
        self.statements.append(stmt)
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        return _Result(self._value)


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


@pytest.mark.asyncio
async def test_database_source_detects_pending_events() -> None:
    session = _Session(value="record-id")
    checker = HeartbeatChecker(
        agent_id="bot",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(session),
            "database_pending_statuses": ["pending"],
        },
    )
    result = await checker.check_events("tenant-a")
    assert result is True
    stmt = session.statements[0]
    compiled = stmt.compile()
    values = list(compiled.params.values())
    assert "tenant-a" in values
    assert "bot" in values
    assert ["pending"] in values


@pytest.mark.asyncio
async def test_database_source_returns_false_when_no_rows() -> None:
    checker = HeartbeatChecker(
        agent_id="bot",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(_Session(value=None)),
        },
    )
    result = await checker.check_events("tenant-a")
    assert result is False


@pytest.mark.asyncio
async def test_database_source_honors_timeout() -> None:
    checker = HeartbeatChecker(
        agent_id="bot",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(_Session(value="row", delay_seconds=0.2)),
            "database_query_timeout_seconds": 0.01,
        },
    )
    started = perf_counter()
    result = await checker.check_events("tenant-a")
    elapsed = perf_counter() - started
    assert result is False
    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_database_source_false_positive_rate_under_one_percent() -> None:
    checker = HeartbeatChecker(
        agent_id="bot",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(_Session(value=None)),
        },
    )
    positives = 0
    for _ in range(100):
        if await checker.check_events("tenant-a"):
            positives += 1
    assert positives <= 1


@pytest.mark.asyncio
async def test_database_source_latency_under_500ms() -> None:
    checker = HeartbeatChecker(
        agent_id="bot",
        config={
            "event_sources": ["database"],
            "database_session_factory": _SessionFactory(_Session(value=None, delay_seconds=0.01)),
        },
    )
    started = perf_counter()
    await checker.check_events("tenant-a")
    elapsed_ms = (perf_counter() - started) * 1000
    assert elapsed_ms < 500
