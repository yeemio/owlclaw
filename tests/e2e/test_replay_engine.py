"""Tests for historical replay components."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from owlclaw.e2e.replay import EventImporter, ReplayComparator, ReplayEngine, ReplayScheduler


def _write_json_events(path: Path) -> None:
    payload = [
        {
            "timestamp": "2026-01-15T09:31:00Z",
            "event_type": "cron",
            "event_name": "hourly_check",
            "payload": {"symbol": "AAPL"},
            "actual_decision": "check_entry_opportunity",
            "actual_result": {"action": "no_entry"},
        },
        {
            "timestamp": "2026-01-15T09:30:00Z",
            "event_type": "cron",
            "event_name": "hourly_check",
            "payload": {"symbol": "TSLA"},
            "actual_decision": "check_entry_opportunity",
            "actual_result": {"action": "entry"},
        },
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_event_importer_json_sort_and_time_filter(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    _write_json_events(source)
    importer = EventImporter()
    start = datetime(2026, 1, 15, 9, 30, 30, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, 9, 31, 30, tzinfo=timezone.utc)

    events = importer.import_events(str(source), format="json", time_range=(start, end))
    assert len(events) == 1
    assert events[0].payload["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_replay_scheduler_accelerated_mode_returns_immediately(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    _write_json_events(source)
    importer = EventImporter()
    events = importer.import_events(str(source), format="json")
    scheduler = ReplayScheduler()

    scheduled = await scheduler.schedule(events, mode="accelerated")
    assert [event.payload["symbol"] for event in scheduled] == ["TSLA", "AAPL"]


@pytest.mark.asyncio
async def test_replay_engine_records_agent_and_cron_decisions(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    _write_json_events(source)
    importer = EventImporter()
    events = importer.import_events(str(source), format="json")
    engine = ReplayEngine()

    result = await engine.replay(events, mode="accelerated")
    assert result.total_events == 2
    assert len(result.agent_decisions) == 2
    assert len(result.cron_decisions) == 2
    assert result.consistency_rate == 1.0
    assert result.memory_growth == [1, 2]


def test_replay_comparator_calculates_consistency_and_distribution(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    _write_json_events(source)
    importer = EventImporter()
    events = importer.import_events(str(source), format="json")
    comparator = ReplayComparator()

    metrics = comparator.compare(
        events,
        agent_decisions=[
            {"decision": "check_entry_opportunity"},
            {"decision": "different_decision"},
        ],
    )
    assert metrics["consistency_rate"] == 0.5
    assert metrics["deviation_distribution"]["low"] == 1
    assert metrics["deviation_distribution"]["medium"] == 1
    assert metrics["quality_trend"] == [1.0, 0.5]
