"""Unit tests for MemoryConfig validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlclaw.agent.memory import MemoryConfig


def test_memory_config_accepts_defaults() -> None:
    config = MemoryConfig()
    assert config.embedding_dimensions == 1536
    assert config.snapshot_recent_hours == 24


@pytest.mark.parametrize(
    "field,value",
    [
        ("embedding_dimensions", 0),
        ("stm_max_tokens", 0),
        ("snapshot_max_tokens", 0),
        ("snapshot_semantic_limit", 0),
        ("snapshot_recent_limit", 0),
        ("time_decay_half_life_hours", 0),
        ("max_entries", 0),
        ("retention_days", 0),
        ("compaction_threshold", 0),
        ("embedding_cache_size", -1),
        ("snapshot_recent_hours", -1),
    ],
)
def test_memory_config_rejects_invalid_numeric_ranges(field: str, value: int | float) -> None:
    with pytest.raises(ValidationError):
        MemoryConfig(**{field: value})
