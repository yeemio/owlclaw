"""Validation tests for LiteLLMEmbedder output shape."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from owlclaw.integrations import llm as llm_integration
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


@pytest.mark.asyncio
async def test_embedder_uses_llm_integration_embedding_facade(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = LiteLLMEmbedder(model="text-embedding-3-small", dimensions=4, cache_size=0)
    captured: dict[str, object] = {}

    async def _fake_aembedding(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "data": [
                {"embedding": [0.1, 0.2, 0.3, 0.4]},
            ]
        }

    monkeypatch.setattr(llm_integration, "aembedding", _fake_aembedding)
    out = await embedder.embed("hello")

    assert out == [0.1, 0.2, 0.3, 0.4]
    assert captured["model"] == "text-embedding-3-small"
    assert captured["input"] == ["hello"]


def test_memory_package_has_no_direct_litellm_imports() -> None:
    memory_dir = Path("owlclaw/agent/memory")
    for py_file in memory_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "litellm", f"{py_file} imports litellm directly"
            if isinstance(node, ast.ImportFrom):
                assert node.module != "litellm", f"{py_file} imports litellm directly"
