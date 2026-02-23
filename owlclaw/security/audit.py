"""Security audit log model for sanitizer/risk/masking events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecurityAuditEvent:
    """Single security audit event."""

    event_type: str
    source: str
    details: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityAuditLog:
    """In-memory audit sink for security-related events."""

    def __init__(self) -> None:
        self._events: list[SecurityAuditEvent] = []

    def record(self, event_type: str, source: str, details: dict[str, Any]) -> SecurityAuditEvent:
        """Record one event and emit debug log."""
        event = SecurityAuditEvent(event_type=event_type, source=source, details=dict(details))
        self._events.append(event)
        logger.info("security audit event type=%s source=%s", event_type, source)
        return event

    def list_events(self) -> list[SecurityAuditEvent]:
        """Return all recorded events."""
        return list(self._events)
