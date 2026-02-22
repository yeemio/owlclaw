"""Memory façade — MemoryService (remember/recall, STM, snapshot)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from owlclaw.agent.memory.embedder import EmbeddingProvider
from owlclaw.agent.memory.models import MemoryConfig, MemoryEntry, MemorySnapshot, RecallResult
from owlclaw.agent.memory.snapshot import SnapshotBuilder
from owlclaw.agent.memory.stm import STMManager
from owlclaw.agent.memory.store import MemoryStore


class MemoryService:
    """Single entry point for memory: Agent Tools and Runtime use this."""

    def __init__(
        self,
        store: MemoryStore,
        embedder: EmbeddingProvider,
        config: MemoryConfig,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._config = config
        self._snapshot_builder = SnapshotBuilder(store, embedder)

    async def remember(
        self,
        agent_id: str,
        tenant_id: str,
        content: str,
        tags: list[str] | None = None,
    ) -> UUID:
        """Store one memory (embed + save). Optionally Ledger can be wired later."""
        embedding = await self._embedder.embed(content)
        entry = MemoryEntry(
            agent_id=agent_id,
            tenant_id=tenant_id,
            content=content,
            embedding=embedding,
            tags=list(tags) if tags else [],
        )
        return await self._store.save(entry)

    async def recall(
        self,
        agent_id: str,
        tenant_id: str,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
    ) -> list[RecallResult]:
        """Search memories by query (embed + search + update access). Returns list of RecallResult."""
        safe_limit = max(1, min(limit, 20))
        query_embedding = await self._embedder.embed(query)
        pairs = await self._store.search(
            agent_id,
            tenant_id,
            query_embedding,
            limit=safe_limit,
            tags=tags,
        )
        if not pairs:
            return []
        entry_ids = [entry.id for entry, _ in pairs]
        await self._store.update_access(agent_id, tenant_id, entry_ids)
        return [RecallResult(entry=entry, score=score) for entry, score in pairs]

    def create_stm(self, max_tokens: int = 2000) -> STMManager:
        """Create per-Run STM manager."""
        return STMManager(max_tokens=max_tokens)

    async def build_snapshot(
        self,
        agent_id: str,
        tenant_id: str,
        trigger_event: str,
        focus: str | None = None,
    ) -> MemorySnapshot:
        """Build LTM snapshot for Run start."""
        return await self._snapshot_builder.build(
            agent_id,
            tenant_id,
            trigger_event,
            focus,
            max_tokens=self._config.snapshot_max_tokens,
        )

    @classmethod
    def from_config(
        cls,
        config: MemoryConfig,
        session_factory: Any = None,
    ) -> MemoryService:
        """Build MemoryService from config: choose store and embedder by vector_backend.

        - vector_backend \"inmemory\": InMemoryStore + RandomEmbedder (mock/tests).
        - vector_backend \"pgvector\": PgVectorStore + LiteLLMEmbedder; session_factory required.
        """
        from owlclaw.agent.memory.embedder_litellm import LiteLLMEmbedder
        from owlclaw.agent.memory.embedder_random import RandomEmbedder
        from owlclaw.agent.memory.store_inmemory import InMemoryStore
        from owlclaw.agent.memory.store_pgvector import PgVectorStore

        if config.vector_backend == "inmemory":
            store: MemoryStore = InMemoryStore(
                time_decay_half_life_hours=config.time_decay_half_life_hours,
            )
            embedder = RandomEmbedder(dimensions=config.embedding_dimensions)
        elif config.vector_backend == "pgvector":
            if session_factory is None:
                raise ValueError("session_factory is required when vector_backend is pgvector")
            store = PgVectorStore(
                session_factory=session_factory,
                embedding_dimensions=config.embedding_dimensions,
                time_decay_half_life_hours=config.time_decay_half_life_hours,
            )
            embedder = LiteLLMEmbedder(
                model=config.embedding_model,
                dimensions=config.embedding_dimensions,
                cache_size=config.embedding_cache_size,
            )
        else:
            raise ValueError(f"Unsupported vector_backend: {config.vector_backend}")
        return cls(store=store, embedder=embedder, config=config)
