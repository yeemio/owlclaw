"""Unit tests for memory CLI dispatch and core logic helpers."""

from __future__ import annotations

import asyncio
import importlib
from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.agent.memory.models import MemoryEntry, SecurityLevel
from owlclaw.agent.memory.store_inmemory import InMemoryStore
from owlclaw.cli.memory import (
    _create_store,
    _list_entries_impl,
    _normalize_backend,
    _prune_impl,
    _reset_impl,
    _security_marker,
    _stats_impl,
    migrate_backend_command,
)


def _seed_store() -> InMemoryStore:
    store = InMemoryStore()
    now = datetime.now(timezone.utc)
    asyncio.run(
        store.save(
            MemoryEntry(
                agent_id="agent-a",
                tenant_id="default",
                content="memory one",
                tags=["alpha", "beta"],
                security_level=SecurityLevel.CONFIDENTIAL,
                created_at=now - timedelta(days=5),
            )
        )
    )
    asyncio.run(
        store.save(
            MemoryEntry(
                agent_id="agent-a",
                tenant_id="default",
                content="memory two",
                tags=["beta"],
                created_at=now - timedelta(days=1),
            )
        )
    )
    asyncio.run(
        store.save(
            MemoryEntry(
                agent_id="agent-b",
                tenant_id="default",
                content="other agent",
                tags=["gamma"],
                created_at=now - timedelta(days=1),
            )
        )
    )
    return store


def test_main_dispatches_memory_list(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_list_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.memory.list_command", _fake_list_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "memory",
            "list",
            "--agent",
            "agent-a",
            "--tenant",
            "t1",
            "--tags",
            "alpha,beta",
            "--page",
            "2",
            "--page-size",
            "5",
            "--include-archived",
            "--backend",
            "inmemory",
        ],
    )
    cli_main.main()
    assert captured["agent"] == "agent-a"
    assert captured["tenant"] == "t1"
    assert captured["tags"] == "alpha,beta"
    assert captured["page"] == 2
    assert captured["page_size"] == 5
    assert captured["include_archived"] is True
    assert captured["backend"] == "inmemory"


def test_main_memory_unknown_subcommand_exits_2(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "memory", "unknown-sub"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 2
    assert "unknown memory subcommand" in capsys.readouterr().err.lower()


def test_main_dispatches_memory_migrate_backend(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.memory.migrate_backend_command", _fake_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "memory",
            "migrate-backend",
            "--agent",
            "agent-a",
            "--tenant",
            "t1",
            "--source-backend",
            "pgvector",
            "--target-backend",
            "qdrant",
            "--batch-size",
            "10",
            "--exclude-archived",
        ],
    )
    cli_main.main()
    assert captured["agent"] == "agent-a"
    assert captured["source_backend"] == "pgvector"
    assert captured["target_backend"] == "qdrant"
    assert captured["batch_size"] == 10
    assert captured["include_archived"] is False


def test_main_memory_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "memory", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    assert "Usage: owlclaw memory [OPTIONS] COMMAND [ARGS]..." in capsys.readouterr().out


def test_list_impl_with_tag_filter() -> None:
    store = _seed_store()
    rows = asyncio.run(
        _list_entries_impl(
            store=store,
            agent="agent-a",
            tenant="default",
            tags=["alpha"],
            page=1,
            page_size=20,
            include_archived=False,
        )
    )
    assert len(rows) == 1
    assert rows[0].content == "memory one"


def test_security_marker_for_confidential() -> None:
    entry = MemoryEntry(content="secret", security_level=SecurityLevel.CONFIDENTIAL)
    assert _security_marker(entry) == "[CONFIDENTIAL] "


def test_prune_impl_by_before_and_tags() -> None:
    store = _seed_store()
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    deleted = asyncio.run(
        _prune_impl(
            store=store,
            agent="agent-a",
            tenant="default",
            before=cutoff,
            tags=["alpha"],
        )
    )
    assert deleted == 1
    remaining = asyncio.run(
        store.list_entries(
            agent_id="agent-a",
            tenant_id="default",
            order_created_asc=False,
            limit=100,
            include_archived=True,
        )
    )
    assert len(remaining) == 1
    assert remaining[0].content == "memory two"


def test_reset_impl_deletes_all_for_agent() -> None:
    store = _seed_store()
    deleted = asyncio.run(_reset_impl(store=store, agent="agent-a", tenant="default"))
    assert deleted == 2


def test_stats_impl_outputs_distribution() -> None:
    store = _seed_store()
    stats = asyncio.run(_stats_impl(store=store, agent="agent-a", tenant="default"))
    assert stats["total_entries"] == 2
    assert stats["tag_distribution"]["alpha"] == 1
    assert stats["tag_distribution"]["beta"] == 2


def test_normalize_backend_accepts_case_and_spaces() -> None:
    assert _normalize_backend("  QDRANT ") == "qdrant"


def test_migrate_backend_rejects_equivalent_backends_after_normalization() -> None:
    with pytest.raises(Exception, match="source and target backend must be different"):
        migrate_backend_command(
            agent="agent-a",
            tenant="default",
            source_backend=" PGVECTOR ",
            target_backend="pgvector",
            batch_size=100,
            include_archived=True,
        )


def test_create_store_qdrant_rejects_empty_collection(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("OWLCLAW_QDRANT_COLLECTION", "   ")
    with pytest.raises(Exception, match="OWLCLAW_QDRANT_COLLECTION must not be empty"):
        _create_store("qdrant")
