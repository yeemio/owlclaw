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
