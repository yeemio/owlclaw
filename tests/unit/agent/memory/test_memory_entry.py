"""Unit tests for MemoryEntry creation and serialization."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from owlclaw.agent.memory.models import MemoryEntry, SecurityLevel


def test_memory_entry_default_creation() -> None:
    """MemoryEntry has sensible defaults and generates id."""
    entry = MemoryEntry()
    assert entry.id is not None
    assert entry.agent_id == ""
    assert entry.tenant_id == ""
    assert entry.content == ""
    assert entry.embedding is None
    assert entry.tags == []
    assert entry.security_level == SecurityLevel.INTERNAL
    assert entry.version == 1
    assert entry.created_at is not None
    assert entry.accessed_at is None
    assert entry.access_count == 0
    assert entry.archived is False


def test_memory_entry_explicit_fields() -> None:
    """MemoryEntry accepts explicit id and all fields."""
    uid = uuid4()
    now = datetime.now(timezone.utc)
    entry = MemoryEntry(
        id=uid,
        agent_id="agent-1",
        tenant_id="tenant-1",
        content="User prefers dark mode",
        embedding=[0.1, 0.2],
        tags=["preference"],
        security_level=SecurityLevel.PUBLIC,
        version=2,
        created_at=now,
        accessed_at=now,
        access_count=3,
        archived=False,
    )
    assert entry.id == uid
    assert entry.agent_id == "agent-1"
    assert entry.content == "User prefers dark mode"
    assert entry.embedding == [0.1, 0.2]
    assert entry.tags == ["preference"]
    assert entry.security_level == SecurityLevel.PUBLIC
    assert entry.access_count == 3


def test_memory_entry_serialization_roundtrip() -> None:
    """Entry can be copied by reconstructing from fields (serialization surrogate)."""
    entry = MemoryEntry(
        agent_id="a",
        tenant_id="t",
        content="hello",
        tags=["x"],
    )
    # Simulate serialization: use dataclass fields as dict
    data = (
        entry.id,
        entry.agent_id,
        entry.tenant_id,
        entry.content,
        entry.embedding,
        tuple(entry.tags),
        entry.security_level,
        entry.version,
        entry.created_at,
        entry.accessed_at,
        entry.access_count,
        entry.archived,
    )
    entry2 = MemoryEntry(
        id=data[0],
        agent_id=data[1],
        tenant_id=data[2],
        content=data[3],
        embedding=list(data[4]) if data[4] else None,
        tags=list(data[5]),
        security_level=data[6],
        version=data[7],
        created_at=data[8],
        accessed_at=data[9],
        access_count=data[10],
        archived=data[11],
    )
    assert entry2.id == entry.id
    assert entry2.content == entry.content
    assert entry2.tags == entry.tags
