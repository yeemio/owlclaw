"""Unit tests for HeartbeatChecker (agent-runtime Task 5.3)."""

from __future__ import annotations

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

    @pytest.mark.asyncio
    async def test_check_events_disabled_returns_false(self) -> None:
        """When disabled, always returns False (no events)."""
        checker = HeartbeatChecker(agent_id="bot", config={"enabled": False})
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
        result = await checker.check_events()
        assert result is False


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
