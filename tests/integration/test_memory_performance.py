"""Performance benchmark for memory recall latency."""

from __future__ import annotations

import asyncio
import os
import random
import statistics
import time

import pytest
from _pytest.fixtures import FixtureLookupError

from owlclaw.agent.memory.embedder_random import RandomEmbedder
from owlclaw.agent.memory.models import MemoryEntry
from owlclaw.agent.memory.store_inmemory import InMemoryStore

pytestmark = pytest.mark.integration


def _has_benchmark_fixture(pytestconfig: pytest.Config) -> bool:
    return pytestconfig.pluginmanager.hasplugin("benchmark")


def test_recall_p95_benchmark_target(pytestconfig: pytest.Config, request: pytest.FixtureRequest) -> None:
    if not _has_benchmark_fixture(pytestconfig):
        pytest.skip("pytest-benchmark plugin not installed")
    try:
        benchmark = request.getfixturevalue("benchmark")
    except FixtureLookupError:
        pytest.skip("benchmark fixture unavailable")

    dataset_size = int(os.getenv("MEMORY_PERF_DATASET_SIZE", "10000"))
    query_runs = int(os.getenv("MEMORY_PERF_QUERY_RUNS", "30"))
    random.seed(7)

    async def _setup() -> tuple[InMemoryStore, list[float]]:
        store = InMemoryStore()
        embedder = RandomEmbedder(dimensions=64)
        for idx in range(dataset_size):
            content = f"memory entry {idx} trading strategy {idx % 97}"
            embedding = await embedder.embed(content)
            await store.save(
                MemoryEntry(
                    agent_id="perf-agent",
                    tenant_id="perf-tenant",
                    content=content,
                    embedding=embedding,
                    tags=["perf"],
                )
            )
        query_embedding = await embedder.embed("trading strategy optimization")
        return store, query_embedding

    store, query_embedding = asyncio.run(_setup())

    latencies_ms: list[float] = []

    async def _one_query() -> None:
        start = time.perf_counter()
        await store.search("perf-agent", "perf-tenant", query_embedding, limit=5)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)

    async def _runner() -> None:
        for _ in range(query_runs):
            await _one_query()

    benchmark(lambda: asyncio.run(_runner()))

    if not latencies_ms:
        pytest.fail("benchmark did not execute any queries")
    p95 = statistics.quantiles(latencies_ms, n=100)[94]
    # Spec target: recall P95 < 200ms.
    assert p95 < 200.0
