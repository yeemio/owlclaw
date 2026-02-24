"""Tests for LangChain version checks."""

from __future__ import annotations

from importlib import metadata

import pytest

from owlclaw.integrations.langchain.version import check_langchain_version


def test_check_langchain_version_accepts_compatible_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_version(name: str) -> str:
        return "0.1.99" if name == "langchain" else "0.2.5"

    monkeypatch.setattr(metadata, "version", fake_version)

    check_langchain_version(min_version="0.1.0", max_version="0.3.0")


def test_check_langchain_version_rejects_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_version(name: str) -> str:
        return "0.3.1"

    monkeypatch.setattr(metadata, "version", fake_version)

    with pytest.raises(ImportError, match="not supported"):
        check_langchain_version(min_version="0.1.0", max_version="0.3.0")


def test_check_langchain_version_rejects_missing_package(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_version(name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", fake_version)

    with pytest.raises(ImportError, match=r"pip install owlclaw\[langchain\]"):
        check_langchain_version(min_version="0.1.0", max_version="0.3.0")
