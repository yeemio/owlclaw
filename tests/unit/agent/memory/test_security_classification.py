"""Unit tests for memory security classification and masking."""

from __future__ import annotations

import pytest

from owlclaw.agent.memory.models import MemoryConfig, MemoryEntry, SecurityLevel
from owlclaw.agent.memory.security import MemorySecurityFilter, SecurityClassifier
from owlclaw.agent.memory.service import MemoryService
from owlclaw.agent.memory.store import MemoryStore


class _DummyEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    @property
    def dimensions(self) -> int:
        return 2


class _CaptureStore(MemoryStore):
    def __init__(self) -> None:
        self.last_saved: MemoryEntry | None = None

    async def save(self, entry: MemoryEntry):
        self.last_saved = entry
        return entry.id

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        limit: int = 5,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[tuple[MemoryEntry, float]]:
        return [
            (
                MemoryEntry(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    content="password=abc123 email alice@example.com",
                    security_level=SecurityLevel.CONFIDENTIAL,
                ),
                0.9,
            )
        ]

    async def get_recent(self, agent_id: str, tenant_id: str, hours: int = 24, limit: int = 5):
        return []

    async def archive(self, entry_ids):
        return 0

    async def delete(self, entry_ids):
        return 0

    async def count(self, agent_id: str, tenant_id: str) -> int:
        return 0

    async def update_access(self, agent_id: str, tenant_id: str, entry_ids):
        return None

    async def list_entries(
        self,
        agent_id: str,
        tenant_id: str,
        order_created_asc: bool,
        limit: int,
        include_archived: bool = False,
    ):
        return []

    async def get_expired_entry_ids(self, agent_id: str, tenant_id: str, before, max_access_count: int = 0):
        return []


def test_security_classifier_levels() -> None:
    classifier = SecurityClassifier()
    assert classifier.classify("my password is 123") == SecurityLevel.CONFIDENTIAL
    assert classifier.classify("contains ssn and passport") == SecurityLevel.RESTRICTED
    assert classifier.classify("regular operational note") == SecurityLevel.INTERNAL


def test_memory_security_filter_masks_sensitive_for_mcp() -> None:
    filt = MemorySecurityFilter()
    entry = MemoryEntry(
        content="email alice@example.com token=secret",
        security_level=SecurityLevel.CONFIDENTIAL,
    )
    masked = filt.for_channel(entry, "mcp")
    assert masked.content != entry.content
    assert "[REDACTED]" in masked.content


def test_memory_security_filter_handles_non_string_channel() -> None:
    filt = MemorySecurityFilter()
    entry = MemoryEntry(
        content="email alice@example.com token=secret",
        security_level=SecurityLevel.CONFIDENTIAL,
    )
    original = filt.for_channel(entry, None)  # type: ignore[arg-type]
    assert original.content == entry.content


@pytest.mark.asyncio
async def test_memory_service_auto_classifies_on_remember() -> None:
    store = _CaptureStore()
    service = MemoryService(store=store, embedder=_DummyEmbedder(), config=MemoryConfig())
    await service.remember("agent-a", "default", "this contains password and token")
    assert store.last_saved is not None
    assert store.last_saved.security_level == SecurityLevel.CONFIDENTIAL


@pytest.mark.asyncio
async def test_memory_service_remember_accepts_sensitivity_override() -> None:
    store = _CaptureStore()
    service = MemoryService(store=store, embedder=_DummyEmbedder(), config=MemoryConfig())
    await service.remember(
        "agent-a",
        "default",
        "this contains password and token",
        sensitivity="public",
    )
    assert store.last_saved is not None
    assert store.last_saved.security_level == SecurityLevel.PUBLIC


@pytest.mark.asyncio
async def test_memory_service_remember_rejects_invalid_sensitivity() -> None:
    store = _CaptureStore()
    service = MemoryService(store=store, embedder=_DummyEmbedder(), config=MemoryConfig())
    with pytest.raises(ValueError, match="sensitivity must be one of"):
        await service.remember(
            "agent-a",
            "default",
            "regular note",
            sensitivity="restricted",
        )


@pytest.mark.asyncio
async def test_memory_service_masks_sensitive_on_mcp_channel() -> None:
    store = _CaptureStore()
    service = MemoryService(store=store, embedder=_DummyEmbedder(), config=MemoryConfig())
    results = await service.recall("agent-a", "default", "query", channel="mcp")
    assert len(results) == 1
    assert "[REDACTED]" in results[0].entry.content
