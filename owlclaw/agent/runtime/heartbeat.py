"""HeartbeatChecker — check pending events to decide if LLM call is needed.

Heartbeat mechanism: when trigger is "heartbeat", no events => skip LLM, save cost.
Event sources (webhook, queue, database, schedule, external_api) are pluggable; MVP uses
placeholder checks returning False until integrations are implemented.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from time import monotonic
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

    def __init__(
        self,
        agent_id: str,
        config: dict[str, Any] | None = None,
        *,
        ledger: Any | None = None,
    ) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self.agent_id = agent_id.strip()
        cfg = config or {}
        self._enabled = self._normalize_enabled(cfg.get("enabled", True))
        self._event_sources = self._normalize_event_sources(
            cfg.get("event_sources", _DEFAULT_EVENT_SOURCES)
        )
        self._ledger = ledger
        self._database_session_factory = cfg.get("database_session_factory")
        self._database_lookback_seconds = self._normalize_positive_number(
            cfg.get("database_lookback_seconds", cfg.get("database_lookback_minutes", 5) * 60),
            default=300.0,
        )
        self._database_query_timeout_seconds = self._normalize_positive_number(
            cfg.get("database_query_timeout_seconds", 0.5),
            default=0.5,
        )
        self._database_latency_warn_ms = self._normalize_positive_number(
            cfg.get("database_latency_warn_ms", 500),
            default=500.0,
        )
        self._database_pending_statuses = self._normalize_pending_statuses(
            cfg.get("database_pending_statuses", ["pending", "queued"]),
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
        elif isinstance(raw_sources, list | tuple | set):
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

    @staticmethod
    def _normalize_positive_number(raw: Any, *, default: float) -> float:
        if isinstance(raw, bool):
            return default
        if isinstance(raw, int | float):
            value = float(raw)
            return value if value > 0 else default
        if isinstance(raw, str):
            value = raw.strip()
            if not value:
                return default
            try:
                parsed = float(value)
            except ValueError:
                return default
            return parsed if parsed > 0 else default
        return default

    @staticmethod
    def _normalize_pending_statuses(raw: Any) -> tuple[str, ...]:
        if isinstance(raw, str):
            items: list[Any] = [raw]
        elif isinstance(raw, list | tuple | set):
            items = list(raw)
        else:
            items = ["pending", "queued"]
        normalized: list[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            status = item.strip().lower()
            if status and status not in normalized:
                normalized.append(status)
        return tuple(normalized or ["pending", "queued"])

    async def check_events(self, tenant_id: str = "default") -> bool:
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
                if await self._check_source(source, tenant_id=tenant_id):
                    logger.info(
                        "HeartbeatChecker found events agent_id=%s source=%s tenant_id=%s",
                        self.agent_id,
                        source,
                        tenant_id,
                    )
                    return True
            except Exception as e:
                logger.warning(
                    "HeartbeatChecker error checking source=%s agent_id=%s tenant_id=%s: %s",
                    source,
                    self.agent_id,
                    tenant_id,
                    e,
                    exc_info=True,
                )
        return False

    async def _check_source(self, source: str, *, tenant_id: str) -> bool:
        """Check a specific event source. Returns True if events exist."""
        if source == "webhook":
            return await self._check_webhook_events()
        if source == "queue":
            return await self._check_queue_events()
        if source == "database":
            return await self._check_database_events(tenant_id=tenant_id)
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

    def _resolve_database_session_factory(self) -> Any | None:
        configured = self._database_session_factory
        if callable(configured):
            return configured
        if self._ledger is None:
            return None
        candidate = getattr(self._ledger, "_session_factory", None)  # noqa: SLF001
        return candidate if callable(candidate) else None

    async def _check_database_events(self, *, tenant_id: str) -> bool:
        """Check pending events via read-only ledger table query."""
        session_factory = self._resolve_database_session_factory()
        if session_factory is None:
            return False

        from sqlalchemy import select

        from owlclaw.governance.ledger import LedgerRecord

        started = monotonic()
        window_start = datetime.now(timezone.utc) - timedelta(seconds=self._database_lookback_seconds)

        async def _query_recent_pending() -> bool:
            async with session_factory() as session:
                stmt = (
                    select(LedgerRecord.id)
                    .where(LedgerRecord.tenant_id == tenant_id)
                    .where(LedgerRecord.agent_id == self.agent_id)
                    .where(LedgerRecord.status.in_(self._database_pending_statuses))
                    .where(LedgerRecord.created_at >= window_start)
                    .order_by(LedgerRecord.created_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none() is not None

        try:
            has_events = await asyncio.wait_for(
                _query_recent_pending(),
                timeout=self._database_query_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "HeartbeatChecker database check timed out agent_id=%s tenant_id=%s timeout=%ss",
                self.agent_id,
                tenant_id,
                self._database_query_timeout_seconds,
            )
            return False
        except Exception:
            logger.warning(
                "HeartbeatChecker database check failed agent_id=%s tenant_id=%s",
                self.agent_id,
                tenant_id,
                exc_info=True,
            )
            return False

        elapsed_ms = (monotonic() - started) * 1000
        if elapsed_ms > self._database_latency_warn_ms:
            logger.warning(
                "HeartbeatChecker database check slow agent_id=%s tenant_id=%s elapsed_ms=%.2f",
                self.agent_id,
                tenant_id,
                elapsed_ms,
            )
        return has_events

    async def _check_schedule_events(self) -> bool:
        """Check for due scheduled tasks. MVP: not implemented, returns False."""
        return False

    async def _check_external_api_events(self) -> bool:
        """Check for external API notifications. MVP: not implemented, returns False."""
        return False
