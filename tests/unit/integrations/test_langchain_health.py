"""Tests for LangChain health status and degradation behavior."""

from __future__ import annotations

import pytest

from owlclaw.integrations.langchain.adapter import LangChainAdapter
from owlclaw.integrations.langchain.config import LangChainConfig


class DummyRegistry:
    def register_handler(self, name, handler):
        return None


class DummyApp:
    def __init__(self):
        self.registry = DummyRegistry()


def test_health_status_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "owlclaw.integrations.langchain.adapter.check_langchain_version",
        lambda **kwargs: None,
    )

    adapter = LangChainAdapter(DummyApp(), LangChainConfig())
    health = adapter.health_status()

    assert health["status"] in {"healthy", "degraded"}
    assert "langchain_available" in health
    assert "config_valid" in health


def test_health_status_degraded_when_langchain_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(**kwargs):
        raise ImportError("langchain missing")

    monkeypatch.setattr("owlclaw.integrations.langchain.adapter.check_langchain_version", _raise)

    adapter = LangChainAdapter(DummyApp(), LangChainConfig())
    health = adapter.health_status()

    assert health["status"] == "degraded"
    assert health["langchain_available"] is False
    assert "langchain missing" in health.get("reason", "")
