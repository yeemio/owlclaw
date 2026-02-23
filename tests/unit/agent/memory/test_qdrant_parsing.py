"""Unit tests for qdrant payload parsing helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from owlclaw.agent.memory.store_qdrant import _entry_from_payload, _parse_dt


def test_parse_dt_accepts_datetime_input() -> None:
    naive = datetime(2026, 1, 1, 10, 0, 0)
    parsed = _parse_dt(naive)
    assert parsed.tzinfo == timezone.utc


def test_entry_from_payload_normalizes_tags_and_access_count() -> None:
    entry = _entry_from_payload(
        uuid4(),
        {
            "agent_id": "a",
            "tenant_id": "t",
            "content": "hello",
            "tags": "single-tag",
            "access_count": "bad",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        vector=[0.1, 0.2],
    )
    assert entry.tags == ["single-tag"]
    assert entry.access_count == 0
