"""Unit tests for QdrantStore with in-memory fake client."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

pytest.importorskip("qdrant_client")

from owlclaw.agent.memory.models import MemoryEntry
from owlclaw.agent.memory.store_qdrant import QdrantStore, _entry_from_payload


@dataclass
class _Point:
    id: str
    payload: dict
    vector: list[float] | None = None
    score: float = 0.9


class _FakeCount:
    def __init__(self, count: int) -> None:
        self.count = count


class _FakeClient:
    def __init__(self) -> None:
        self.data: dict[str, _Point] = {}

    async def collection_exists(self, _: str) -> bool:
        return True

    async def create_collection(self, **kwargs) -> None:  # noqa: ARG002
        return None

    async def upsert(self, collection_name: str, points: list) -> None:  # noqa: ARG002
        for point in points:
            self.data[str(point.id)] = _Point(id=str(point.id), payload=point.payload, vector=point.vector, score=0.9)

    async def search(self, **kwargs) -> list[_Point]:
        return list(self.data.values())

    async def scroll(self, **kwargs) -> tuple[list[_Point], None]:
        return list(self.data.values()), None

    async def set_payload(self, collection_name: str, payload: dict, points: list[str]) -> None:  # noqa: ARG002
        for pid in points:
            self.data[pid].payload.update(payload)

    async def delete(self, collection_name: str, points_selector) -> None:  # noqa: ARG002, ANN001
        for pid in list(points_selector.points):
            self.data.pop(str(pid), None)

    async def count(self, **kwargs) -> _FakeCount:
        count = sum(1 for p in self.data.values() if not p.payload.get("archived", False))
        return _FakeCount(count)

    async def retrieve(self, collection_name: str, ids: list[str], with_payload: bool, with_vectors: bool) -> list[_Point]:  # noqa: ARG002
        return [self.data[i] for i in ids if i in self.data]


@pytest.mark.asyncio
async def test_qdrant_store_save_search_archive_delete() -> None:
    store = QdrantStore(
        url="http://unused:6333",
        collection_name="test",
        embedding_dimensions=3,
        client=_FakeClient(),
    )
    entry = MemoryEntry(agent_id="a", tenant_id="t", content="hello", embedding=[0.1, 0.2, 0.3], tags=["x"])
    await store.save(entry)

    hits = await store.search("a", "t", [0.1, 0.2, 0.3], limit=5)
    assert len(hits) == 1
    assert hits[0][0].content == "hello"
    assert await store.count("a", "t") == 1

    archived = await store.archive([entry.id])
    assert archived == 1
    assert await store.count("a", "t") == 0

    deleted = await store.delete([entry.id])
    assert deleted == 1


def test_entry_from_payload_tolerates_invalid_types() -> None:
    entry = _entry_from_payload(
        uuid4(),
        {
            "agent_id": "a",
            "tenant_id": "t",
            "content": "hello",
            "version": "not-an-int",
            "created_at": "bad-datetime",
            "access_count": object(),
            "archived": "false",
        },
        vector=[0.1, 0.2],
    )
    assert entry.version == 1
    assert entry.access_count == 0
    assert entry.archived is False
