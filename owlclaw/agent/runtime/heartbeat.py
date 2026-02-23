"""HeartbeatChecker — check pending events to decide if LLM call is needed.

Heartbeat mechanism: when trigger is "heartbeat", no events => skip LLM, save cost.
Event sources (webhook, queue, database, schedule, external_api) are pluggable; MVP uses
placeholder checks returning False until integrations are implemented.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_EVENT_SOURCES = ["webhook", "queue", "database", "schedule", "external_api"]
_SUPPORTED_EVENT_SOURCES = frozenset(_DEFAULT_EVENT_SOURCES)


class HeartbeatChecker:
    """Check for pending events to decide if LLM call is needed.

    When Heartbeat triggers an Agent run, this checker queries configured
    event sources. If no source reports events, the run can be skipped
    (no LLM call) to save cost.

    Args:
        agent_id: Stable identifier for the Agent.
        config: Heartbeat configuration. Keys:
            - event_sources: list of source names to check (default: webhook,
              queue, database, schedule, external_api)
            - enabled: if False, check_events() always returns False
    """

    def __init__(self, agent_id: str, config: dict[str, Any] | None = None) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self.agent_id = agent_id.strip()
        cfg = config or {}
        self._enabled = self._normalize_enabled(cfg.get("enabled", True))
        self._event_sources = self._normalize_event_sources(
            cfg.get("event_sources", _DEFAULT_EVENT_SOURCES)
        )

    @staticmethod
    def _normalize_enabled(raw_enabled: Any) -> bool:
        """Normalize enabled flag from bool/string values."""
        if isinstance(raw_enabled, bool):
            return raw_enabled
        if isinstance(raw_enabled, str):
            value = raw_enabled.strip().lower()
            if value in {"false", "0", "no", "off"}:
                return False
            if value in {"true", "1", "yes", "on"}:
                return True
        return bool(raw_enabled)

    @staticmethod
    def _normalize_event_sources(raw_sources: Any) -> list[str]:
        """Normalize event_sources config into a deduplicated string list."""
        if isinstance(raw_sources, str):
            items = [raw_sources]
        elif isinstance(raw_sources, (list, tuple, set)):
            if len(raw_sources) == 0:
                return []
            items = list(raw_sources)
        else:
            return list(_DEFAULT_EVENT_SOURCES)

        normalized: list[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            source = item.strip().lower()
            if source and source in _SUPPORTED_EVENT_SOURCES and source not in normalized:
                normalized.append(source)
        return normalized if normalized else list(_DEFAULT_EVENT_SOURCES)

    async def check_events(self) -> bool:
        """Check if there are pending events in any configured source.

        Returns:
            True if any source has events, False otherwise.
            When disabled, always returns False (no events).
        """
        if not self._enabled:
            logger.debug(
                "HeartbeatChecker disabled agent_id=%s, assuming no events",
                self.agent_id,
            )
            return False

        for source in self._event_sources:
            try:
                if await self._check_source(source):
                    logger.info(
                        "HeartbeatChecker found events agent_id=%s source=%s",
                        self.agent_id,
                        source,
                    )
                    return True
            except Exception as e:
                logger.warning(
                    "HeartbeatChecker error checking source=%s agent_id=%s: %s",
                    source,
                    self.agent_id,
                    e,
                    exc_info=True,
                )
        return False

    async def _check_source(self, source: str) -> bool:
        """Check a specific event source. Returns True if events exist."""
        if source == "webhook":
            return await self._check_webhook_events()
        if source == "queue":
            return await self._check_queue_events()
        if source == "database":
            return await self._check_database_events()
        if source == "schedule":
            return await self._check_schedule_events()
        if source == "external_api":
            return await self._check_external_api_events()
        logger.warning("HeartbeatChecker unknown source=%s", source)
        return False

    async def _check_webhook_events(self) -> bool:
        """Check for new webhook events. MVP: not implemented, returns False."""
        return False

    async def _check_queue_events(self) -> bool:
        """Check for new queue messages. MVP: not implemented, returns False."""
        return False

    async def _check_database_events(self) -> bool:
        """Check for database change events. MVP: not implemented, returns False."""
        return False

    async def _check_schedule_events(self) -> bool:
        """Check for due scheduled tasks. MVP: not implemented, returns False."""
        return False

    async def _check_external_api_events(self) -> bool:
        """Check for external API notifications. MVP: not implemented, returns False."""
        return False
