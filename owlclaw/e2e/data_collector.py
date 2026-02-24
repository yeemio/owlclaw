"""In-memory data collector for e2e execution telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from owlclaw.e2e.models import ExecutionEvent


@dataclass
class CollectedData:
    """Collected telemetry for one execution."""

    execution_id: str
    events: list[ExecutionEvent] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    traces: list[dict[str, Any]] = field(default_factory=list)
    resource_usage: dict[str, float] = field(default_factory=dict)


class DataCollector:
    """Collect events, metrics, and errors during one execution run."""

    def __init__(self) -> None:
        self._execution_id: str | None = None
        self._events: list[ExecutionEvent] = []
        self._metrics: dict[str, float] = {}
        self._errors: list[str] = []
        self._traces: list[dict[str, Any]] = []
        self._resource_usage: dict[str, float] = {}

    def start_collection(self, execution_id: str) -> None:
        """Start a fresh collection scope."""
        if not execution_id.strip():
            raise ValueError("execution_id must be non-empty")
        self._execution_id = execution_id
        self._events.clear()
        self._metrics.clear()
        self._errors.clear()
        self._traces.clear()
        self._resource_usage.clear()

    def record_event(
        self,
        *,
        event_type: str,
        message: str = "",
        data: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record one component event."""
        self._require_started()
        event = ExecutionEvent(
            timestamp=timestamp or datetime.now(timezone.utc),
            event_type=event_type,
            message=message,
            data=data or {},
        )
        self._events.append(event)

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record one metric value."""
        self._require_started()
        self._metrics[metric_name] = float(value)

    def record_error(self, error: str) -> None:
        """Record one error message."""
        self._require_started()
        self._errors.append(error)

    def record_trace(self, trace: dict[str, Any]) -> None:
        """Record one execution trace entry."""
        self._require_started()
        self._traces.append(dict(trace))

    def record_resource_usage(self, key: str, value: float) -> None:
        """Record one resource usage metric."""
        self._require_started()
        self._resource_usage[key] = float(value)

    def stop_collection(self) -> CollectedData:
        """Finish collection and return a snapshot."""
        self._require_started()
        assert self._execution_id is not None
        return CollectedData(
            execution_id=self._execution_id,
            events=list(self._events),
            metrics=dict(self._metrics),
            errors=list(self._errors),
            traces=list(self._traces),
            resource_usage=dict(self._resource_usage),
        )

    def _require_started(self) -> None:
        if self._execution_id is None:
            raise RuntimeError("start_collection() must be called first")
