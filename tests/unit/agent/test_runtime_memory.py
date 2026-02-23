"""Unit and property tests for runtime MemorySystem (agent-runtime Task 3.1/3.2/3.3)."""

from __future__ import annotations

from pathlib import Path
import pytest
from hypothesis import HealthCheck
from hypothesis import given
from hypothesis import settings
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


def test_long_term_write_appends_memory_file_and_indexes(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []

    class _Index:
        def upsert(self, payload):  # type: ignore[no-untyped-def]
            events.append(payload)

    memory_path = tmp_path / "MEMORY.md"
    memory = MemorySystem(memory_file=str(memory_path), vector_index=_Index())
    record = memory.write("Important lesson", tags=["Risk", "Ops"])
    assert "important lesson" in memory_path.read_text(encoding="utf-8").lower()
    assert record["tags"] == ["risk", "ops"]
    assert len(events) == 1
    assert events[0]["content"] == "Important lesson"


def test_long_term_search_and_recall_relevant() -> None:
    memory = MemorySystem()
    memory.write("apple revenue grew strongly", tags=["finance"])
    memory.write("weather is rainy in beijing", tags=["weather"])
    hits = memory.search("apple growth", limit=2)
    assert hits
    assert "apple" in hits[0]["content"].lower()
    recalled = memory.recall_relevant("apple growth", limit=1)
    assert len(recalled) == 1
    assert "apple" in recalled[0]


def test_memory_file_size_limit_rotates_archive(tmp_path: Path) -> None:
    memory_path = tmp_path / "MEMORY.md"
    memory = MemorySystem(memory_file=str(memory_path), memory_file_size_limit_bytes=1024)
    for _ in range(40):
        memory.write("x" * 120, tags=["archive"])
    archives = list(tmp_path.glob("MEMORY.*.archive.md"))
    assert archives
    assert memory_path.exists()
    assert "rotated" in memory_path.read_text(encoding="utf-8").lower()


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


@given(
    content=st.text(min_size=1, max_size=120).filter(lambda s: s.strip() != "" and "\n" not in s and "\r" not in s),
    tags=st.lists(st.text(min_size=1, max_size=12), min_size=0, max_size=4),
)
@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_long_term_write_round_trip(content: str, tags: list[str], tmp_path: Path) -> None:
    """Property 6: write() persists retrievable long-term record (round-trip)."""
    memory_path = tmp_path / "MEMORY.md"
    memory = MemorySystem(memory_file=str(memory_path))
    memory.write(content, tags=tags)
    hits = memory.search(content, limit=1)
    assert hits
    assert hits[0]["content"] == content.strip()


@given(
    pair=st.tuples(
        st.text(
            alphabet=st.characters(whitelist_categories=["Ll", "Lu", "Nd"]),
            min_size=1,
            max_size=20,
        ),
        st.text(
            alphabet=st.characters(whitelist_categories=["Ll", "Lu", "Nd"]),
            min_size=1,
            max_size=20,
        ),
    ).filter(lambda p: p[0] != p[1]),
)
@settings(deadline=None)
def test_property_vector_search_relevance(pair: tuple[str, str]) -> None:
    """Property 7: query-relevant memory ranks ahead of unrelated memory."""
    topic, other = pair
    memory = MemorySystem()
    memory.write(f"{topic} alpha strategy", tags=["t"])
    memory.write(f"{other} beta update", tags=["o"])
    results = memory.search(topic, limit=2)
    assert results
    assert topic.lower() in results[0]["content"].lower()


@given(
    payload=st.lists(
        st.text(min_size=40, max_size=60).filter(lambda s: s.strip() != "" and "\n" not in s and "\r" not in s),
        min_size=50,
        max_size=60,
    )
)
@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_memory_file_size_limit(payload: list[str], tmp_path: Path) -> None:
    """Property 8: memory file is rotated when size exceeds configured limit."""
    memory_path = tmp_path / "MEMORY.md"
    memory = MemorySystem(memory_file=str(memory_path), memory_file_size_limit_bytes=1024)
    for item in payload:
        memory.write(item, tags=["limit"])
    archives = list(tmp_path.glob("MEMORY.*.archive.md"))
    assert archives
