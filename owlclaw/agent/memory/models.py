"""Data models for Agent Memory — MemoryEntry, SecurityLevel, MemoryConfig."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel


class SecurityLevel(str, Enum):
    """Security classification for a memory entry."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class MemoryEntry:
    """Single long-term memory entry (STM/LTM layer)."""

    id: UUID = field(default_factory=uuid4)
    agent_id: str = ""
    tenant_id: str = ""
    content: str = ""
    embedding: list[float] | None = None
    tags: list[str] = field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime | None = None
    access_count: int = 0
    archived: bool = False


@dataclass
class MemorySnapshot:
    """Preloaded LTM snapshot for a Run: prompt fragment + source entry ids."""

    prompt_fragment: str = ""
    entry_ids: list[UUID] = field(default_factory=list)


@dataclass
class RecallResult:
    """Single result from recall(): entry and similarity score."""

    entry: MemoryEntry = field(default_factory=MemoryEntry)
    score: float = 0.0


class MemoryConfig(BaseModel):
    """Pydantic model for owlclaw.yaml memory section."""

    vector_backend: str = "pgvector"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    stm_max_tokens: int = 2000
    snapshot_max_tokens: int = 500
    snapshot_semantic_limit: int = 3
    snapshot_recent_hours: int = 24
    snapshot_recent_limit: int = 5
    time_decay_half_life_hours: float = 168.0
    max_entries: int = 10000
    retention_days: int = 365
    compaction_threshold: int = 50
    embedding_cache_size: int = 1000

    class Config:
        extra = "ignore"
