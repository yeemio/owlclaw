"""Unit tests for TFIDFEmbedder fallback provider."""

from __future__ import annotations

import pytest

pytest.importorskip("sklearn")

from owlclaw.agent.memory.embedder_tfidf import TFIDFEmbedder


@pytest.mark.asyncio
async def test_tfidf_embedder_returns_fixed_dimensions() -> None:
    embedder = TFIDFEmbedder(dimensions=32)
    vec = await embedder.embed("memory fallback example")
    assert len(vec) == 32
    assert any(v > 0 for v in vec)


@pytest.mark.asyncio
async def test_tfidf_embedder_batch() -> None:
    embedder = TFIDFEmbedder(dimensions=16)
    vectors = await embedder.embed_batch(["alpha beta", "beta gamma"])
    assert len(vectors) == 2
    assert all(len(v) == 16 for v in vectors)
