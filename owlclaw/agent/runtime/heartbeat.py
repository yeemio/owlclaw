"""HeartbeatChecker — check pending events to decide if LLM call is needed.

Heartbeat mechanism: when trigger is "heartbeat", no events => skip LLM, save cost.
Event sources (webhook, queue, database, schedule) are pluggable; MVP uses
placeholder checks returning False until integrations are implemented.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_EVENT_SOURCES = ["webhook", "queue", "database", "schedule"]


class HeartbeatChecker:
    """Check for pending events to decide if LLM call is needed.

    When Heartbeat triggers an Agent run, this checker queries configured
    event sources. If no source reports events, the run can be skipped
    (no LLM call) to save cost.

    Args:
        agent_id: Stable identifier for the Agent.
        config: Heartbeat configuration. Keys:
            - event_sources: list of source names to check (default: webhook,
              queue, database, schedule)
            - enabled: if False, check_events() always returns False
    """

    def __init__(self, agent_id: str, config: dict[str, Any] | None = None) -> None:
        self.agent_id = agent_id
        cfg = config or {}
        self._enabled = cfg.get("enabled", True)
        self._event_sources: list[str] = cfg.get(
            "event_sources", _DEFAULT_EVENT_SOURCES
        )

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
