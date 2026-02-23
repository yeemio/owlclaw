"""Unit and property tests for runtime MemorySystem (agent-runtime Task 3.1/3.2/3.3)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.agent.runtime.memory import MemorySystem


def test_add_short_term_and_build_context() -> None:
    memory = MemorySystem(short_term_token_limit=50)
    memory.add_short_term("trigger", "cron event arrived")
    memory.add_short_term("tool", "market scan completed")
    context = memory.build_short_term_context()
    assert "trigger: cron event arrived" in context
    assert "tool: market scan completed" in context


def test_add_short_term_validates_inputs() -> None:
    memory = MemorySystem(short_term_token_limit=10)
    with pytest.raises(ValueError, match="role must be a non-empty string"):
        memory.add_short_term("", "x")
    with pytest.raises(ValueError, match="content must be a non-empty string"):
        memory.add_short_term("user", " ")


@given(
    limit=st.integers(min_value=5, max_value=60),
    entries=st.lists(
        st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != "" and "\n" not in s),
        min_size=1,
        max_size=12,
    ),
)
@settings(deadline=None)
def test_property_short_term_token_limit(limit: int, entries: list[str]) -> None:
    """Property 4: built short-term context respects configured token limit."""
    memory = MemorySystem(short_term_token_limit=limit)
    for item in entries:
        memory.add_short_term("event", item)
    context = memory.build_short_term_context()
    assert memory.estimate_tokens(context) <= limit + 4  # allow compression header words


@given(
    limit=st.integers(min_value=5, max_value=20),
    words=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=["Cc", "Cs", "Zl", "Zp"]),
            min_size=1,
            max_size=12,
        ).filter(lambda s: s.strip() != "" and "\n" not in s and "\r" not in s),
        min_size=25,
        max_size=60,
    ),
)
@settings(deadline=None)
def test_property_short_term_auto_compression(limit: int, words: list[str]) -> None:
    """Property 5: context auto-compresses when over token budget and keeps latest signal."""
    memory = MemorySystem(short_term_token_limit=limit)
    for i, word in enumerate(words):
        memory.add_short_term("event", f"{word} {i}")
    context = memory.build_short_term_context()
    assert context
    assert memory.estimate_tokens(context) <= limit + 4
    assert f" {len(words)-1}" in context
    assert "[compressed " in context
