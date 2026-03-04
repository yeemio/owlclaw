"""Tests for optional pgvector dependency behavior."""

from __future__ import annotations

import builtins
import importlib
import sys
from types import ModuleType

import pytest


def test_memory_module_imports_without_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name.startswith("pgvector"):
            raise ModuleNotFoundError("No module named 'pgvector'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    sys.modules.pop("owlclaw.agent.memory", None)
    sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)
    try:
        module = importlib.import_module("owlclaw.agent.memory")
        assert isinstance(module, ModuleType)
        assert hasattr(module, "InMemoryStore")
        assert hasattr(module, "PgVectorStore")
    finally:
        sys.modules.pop("owlclaw.agent.memory", None)
        sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)


def test_pgvector_store_stub_raises_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name.startswith("pgvector"):
            raise ModuleNotFoundError("No module named 'pgvector'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    sys.modules.pop("owlclaw.agent.memory", None)
    sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)
    try:
        memory_module = importlib.import_module("owlclaw.agent.memory")
        with pytest.raises(ModuleNotFoundError, match="pgvector is required for PgVectorStore"):
            memory_module.PgVectorStore(session_factory=None)  # type: ignore[call-arg]
    finally:
        sys.modules.pop("owlclaw.agent.memory", None)
        sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)


def test_store_inmemory_imports_without_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name.startswith("pgvector"):
            raise ModuleNotFoundError("No module named 'pgvector'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    sys.modules.pop("owlclaw.agent.memory.store_inmemory", None)
    sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)
    try:
        module = importlib.import_module("owlclaw.agent.memory.store_inmemory")
        assert isinstance(module, ModuleType)
        assert hasattr(module, "InMemoryStore")
    finally:
        sys.modules.pop("owlclaw.agent.memory.store_inmemory", None)
        sys.modules.pop("owlclaw.agent.memory.store_pgvector", None)
