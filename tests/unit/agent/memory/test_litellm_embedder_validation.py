"""Validation tests for LiteLLMEmbedder output shape."""

from __future__ import annotations

import pytest

from owlclaw.agent.memory.embedder_litellm import LiteLLMEmbedder


@pytest.mark.asyncio
async def test_embed_raises_on_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = LiteLLMEmbedder(model="text-embedding-3-small", dimensions=4, cache_size=0)

    async def _fake_call(_: list[str]) -> list[list[float]]:
        return [[0.1, 0.2]]

    monkeypatch.setattr(embedder, "_call_aembedding", _fake_call)

    with pytest.raises(ValueError, match="expected 4, got 2"):
        await embedder.embed("hello")


@pytest.mark.asyncio
async def test_embed_batch_raises_on_count_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = LiteLLMEmbedder(model="text-embedding-3-small", dimensions=4, cache_size=0)

    async def _fake_call(_: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4]]

    monkeypatch.setattr(embedder, "_call_aembedding", _fake_call)

    with pytest.raises(ValueError, match="expected 2, got 1"):
        await embedder.embed_batch(["a", "b"])
