"""Unit tests for OwlHub production release-gate checks."""

from __future__ import annotations

import json
from pathlib import Path

from owlclaw.owlhub.release_gate import (
    check_api_health,
    check_api_metrics,
    check_cli_search,
    check_index_access,
    run_release_gate,
)


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_check_api_health_ok(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ARG001
        return _FakeResponse(json.dumps({"status": "ok"}))

    monkeypatch.setattr("owlclaw.owlhub.release_gate.urlopen", fake_urlopen)
    result = check_api_health("https://hub.example.com")
    assert result.passed is True


def test_check_api_metrics_has_prometheus_prefix(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ARG001
        return _FakeResponse("owlhub_requests_total 42\n")

    monkeypatch.setattr("owlclaw.owlhub.release_gate.urlopen", fake_urlopen)
    result = check_api_metrics("https://hub.example.com")
    assert result.passed is True


def test_check_index_access_valid_payload(monkeypatch) -> None:
    payload = {"skills": [{"manifest": {"name": "demo"}}]}

    def fake_urlopen(request, timeout):  # noqa: ARG001
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr("owlclaw.owlhub.release_gate.urlopen", fake_urlopen)
    result = check_index_access("https://hub.example.com/index.json")
    assert result.passed is True


def test_check_cli_search_uses_client(monkeypatch, tmp_path: Path) -> None:
    class _FakeClient:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            _ = kwargs

        def search(self, query: str):  # type: ignore[no-untyped-def]
            return [{"name": "demo"}] if query == "skill" else []

    monkeypatch.setattr("owlclaw.owlhub.release_gate.OwlHubClient", _FakeClient)
    result = check_cli_search(
        index_url="https://hub.example.com/index.json",
        query="skill",
        install_dir=tmp_path / "skills",
        lock_file=tmp_path / "skill-lock.json",
    )
    assert result.passed is True


def test_run_release_gate_all_checks_pass(monkeypatch, tmp_path: Path) -> None:
    def fake_urlopen(request, timeout):  # noqa: ARG001
        full_url = request.full_url
        if full_url.endswith("/health"):
            return _FakeResponse(json.dumps({"status": "ok"}))
        if full_url.endswith("/metrics"):
            return _FakeResponse("http_requests_total 1\n")
        return _FakeResponse(json.dumps({"skills": [{"manifest": {"name": "demo"}}]}))

    class _FakeClient:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            _ = kwargs

        def search(self, query: str):  # type: ignore[no-untyped-def]
            return [{"name": query}]

    monkeypatch.setattr("owlclaw.owlhub.release_gate.urlopen", fake_urlopen)
    monkeypatch.setattr("owlclaw.owlhub.release_gate.OwlHubClient", _FakeClient)
    report = run_release_gate(
        api_base_url="https://hub.example.com",
        index_url="https://hub.example.com/index.json",
        query="skill",
        work_dir=tmp_path,
    )
    assert report.passed is True
    assert len(report.checks) == 4
