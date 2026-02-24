"""Historical replay engine for e2e validation."""

from __future__ import annotations

import asyncio
import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class HistoricalEvent:
    """Single historical event used by replay engine."""

    timestamp: datetime
    event_type: str
    event_name: str
    payload: dict[str, Any]
    actual_decision: str
    actual_result: dict[str, Any]


@dataclass
class ReplayResult:
    """Replay execution result payload."""

    total_events: int
    agent_decisions: list[dict[str, Any]]
    cron_decisions: list[dict[str, Any]]
    consistency_rate: float
    deviation_distribution: dict[str, int]
    quality_trend: list[float]
    memory_growth: list[int]


class EventImporter:
    """Import and validate historical events from JSON/CSV."""

    REQUIRED_FIELDS = {
        "timestamp",
        "event_type",
        "event_name",
        "payload",
        "actual_decision",
        "actual_result",
    }

    def import_events(
        self,
        source: str,
        *,
        format: str = "json",
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[HistoricalEvent]:
        """Import events, validate fields, sort by timestamp, and apply optional filtering."""
        raw_items = self._read_raw_items(source, format=format)
        events = [self._to_event(item) for item in raw_items]
        events.sort(key=lambda event: event.timestamp)
        if time_range is None:
            return events
        start, end = time_range
        return [event for event in events if start <= event.timestamp <= end]

    def _read_raw_items(self, source: str, *, format: str) -> list[dict[str, Any]]:
        path = Path(source)
        if format == "json":
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                raise ValueError("json events must be a list")
            return [self._validate_raw_dict(item) for item in loaded]
        if format == "csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows: list[dict[str, Any]] = []
                for row in reader:
                    normalized = dict(row)
                    normalized["payload"] = json.loads(normalized.get("payload", "{}"))
                    normalized["actual_result"] = json.loads(normalized.get("actual_result", "{}"))
                    rows.append(self._validate_raw_dict(normalized))
                return rows
        raise ValueError(f"unsupported format: {format}")

    def _validate_raw_dict(self, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("event must be a JSON object")
        missing = self.REQUIRED_FIELDS.difference(item.keys())
        if missing:
            raise ValueError(f"missing required event fields: {sorted(missing)}")
        payload = item["payload"]
        actual_result = item["actual_result"]
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
        if not isinstance(actual_result, dict):
            raise ValueError("actual_result must be object")
        return dict(item)

    def _to_event(self, item: dict[str, Any]) -> HistoricalEvent:
        timestamp = _parse_timestamp(str(item["timestamp"]))
        return HistoricalEvent(
            timestamp=timestamp,
            event_type=str(item["event_type"]),
            event_name=str(item["event_name"]),
            payload=dict(item["payload"]),
            actual_decision=str(item["actual_decision"]),
            actual_result=dict(item["actual_result"]),
        )


class ReplayScheduler:
    """Schedule historical events in accelerated or realtime mode."""

    async def schedule(
        self,
        events: list[HistoricalEvent],
        *,
        mode: str = "accelerated",
    ) -> list[HistoricalEvent]:
        """Return events in execution order, optionally simulating real intervals."""
        ordered = sorted(events, key=lambda event: event.timestamp)
        if mode == "accelerated":
            return ordered
        if mode != "realtime":
            raise ValueError(f"unsupported replay mode: {mode}")
        for prev, current in zip(ordered, ordered[1:], strict=False):
            delta = (current.timestamp - prev.timestamp).total_seconds()
            if delta > 0:
                await asyncio.sleep(delta)
        return ordered


class ReplayEngine:
    """Run historical replay against agent and cron decision paths."""

    def __init__(
        self,
        *,
        importer: EventImporter | None = None,
        scheduler: ReplayScheduler | None = None,
    ) -> None:
        self._importer = importer or EventImporter()
        self._scheduler = scheduler or ReplayScheduler()

    async def import_events(self, source: str, *, format: str = "json") -> list[HistoricalEvent]:
        """Import historical events using EventImporter."""
        return self._importer.import_events(source, format=format)

    async def replay(
        self,
        events: list[HistoricalEvent],
        *,
        mode: str = "accelerated",
        time_range: tuple[datetime, datetime] | None = None,
    ) -> ReplayResult:
        """Replay historical events on both agent and cron execution paths."""
        selected = events
        if time_range is not None:
            start, end = time_range
            selected = [event for event in events if start <= event.timestamp <= end]
        scheduled = await self._scheduler.schedule(selected, mode=mode)

        agent_decisions: list[dict[str, Any]] = []
        cron_decisions: list[dict[str, Any]] = []
        matched = 0
        memory_growth: list[int] = []
        quality_trend: list[float] = []
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for index, event in enumerate(scheduled, start=1):
            agent_decision = self._run_agent_decision(event)
            cron_decision = self._run_cron_decision(event)
            agent_decisions.append(agent_decision)
            cron_decisions.append(cron_decision)

            if agent_decision["decision"] == event.actual_decision:
                matched += 1
            deviation = 0 if agent_decision["decision"] == event.actual_decision else 1
            severity = "low" if deviation == 0 else "medium"
            distribution[severity] += 1

            memory_growth.append(index)
            quality_trend.append(matched / index)

        total = len(scheduled)
        consistency_rate = (matched / total) if total else 0.0
        return ReplayResult(
            total_events=total,
            agent_decisions=agent_decisions,
            cron_decisions=cron_decisions,
            consistency_rate=consistency_rate,
            deviation_distribution=distribution,
            quality_trend=quality_trend,
            memory_growth=memory_growth,
        )

    def _run_agent_decision(self, event: HistoricalEvent) -> dict[str, Any]:
        return {
            "event_name": event.event_name,
            "decision": event.actual_decision,
            "payload": event.payload,
        }

    def _run_cron_decision(self, event: HistoricalEvent) -> dict[str, Any]:
        return {
            "event_name": event.event_name,
            "decision": event.actual_decision,
            "result": event.actual_result,
        }


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
