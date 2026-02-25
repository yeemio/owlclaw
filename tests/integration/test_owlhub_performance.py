"""Performance checks for OwlHub API and CLI client (owlhub Task 30.3)."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request

import pytest
from fastapi.testclient import TestClient

from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index

pytestmark = pytest.mark.integration


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _p95_ms(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def _build_index(path: Path, *, total: int) -> None:
    skills: list[dict[str, object]] = []
    for i in range(total):
        skills.append(
            {
                "manifest": {
                    "name": f"skill-{i:04d}",
                    "publisher": "acme",
                    "version": f"1.{i % 5}.0",
                    "description": f"performance search skill {i}",
                    "tags": ["perf", f"group-{i % 10}"],
                    "dependencies": {},
                },
                "version_state": "released",
                "updated_at": f"2026-02-{(i % 28) + 1:02d}T00:00:00+00:00",
                "statistics": {"total_downloads": i * 3},
            }
        )
    payload = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": total,
        "skills": skills,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _set_index_env(index_path: Path) -> dict[str, str | None]:
    old = {"OWLHUB_INDEX_PATH": os.getenv("OWLHUB_INDEX_PATH")}
    os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
    _load_index.cache_clear()
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    value = old.get("OWLHUB_INDEX_PATH")
    if value is None:
        os.environ.pop("OWLHUB_INDEX_PATH", None)
    else:
        os.environ["OWLHUB_INDEX_PATH"] = value
    _load_index.cache_clear()


def test_performance_search_response_time_p95_under_500ms(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _build_index(index_path, total=2000)
    old = _set_index_env(index_path)
    try:
        client = TestClient(create_app())
        latencies_ms: list[float] = []
        for _ in range(40):
            started = time.perf_counter()
            response = client.get("/api/v1/skills", params={"query": "skill", "page_size": 50})
            latencies_ms.append((time.perf_counter() - started) * 1000.0)
            assert response.status_code == 200
            assert response.json()["total"] == 2000
        assert _p95_ms(latencies_ms) < 500.0
    finally:
        _restore_env(old)


def test_performance_concurrent_api_requests_handling(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _build_index(index_path, total=1000)
    old = _set_index_env(index_path)
    try:
        client = TestClient(create_app())

        def call_once(_: int) -> int:
            response = client.get("/api/v1/skills", params={"query": "skill", "page_size": 20})
            return response.status_code

        total_requests = 120
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=16) as pool:
            statuses = list(pool.map(call_once, range(total_requests)))
        elapsed = time.perf_counter() - started
        assert all(status == 200 for status in statuses)
        assert elapsed < 15.0
    finally:
        _restore_env(old)


def test_performance_cache_hit_miss_behavior_for_remote_index(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "remote-index.json"
    _build_index(index_path, total=400)
    payload = index_path.read_text(encoding="utf-8")
    calls = {"count": 0}

    def delayed_urlopen(request_or_url: Request | str, timeout: int):  # noqa: ARG001
        _ = request_or_url
        calls["count"] += 1
        time.sleep(0.05)
        return _FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", delayed_urlopen)
    client = OwlHubClient(
        index_url="http://hub.local/index.json",
        install_dir=tmp_path / "skills",
        lock_file=tmp_path / "lock.json",
    )

    start_miss = time.perf_counter()
    miss = client.search(query="skill")
    _ = (time.perf_counter() - start_miss) * 1000.0
    assert len(miss) == 400

    start_hit = time.perf_counter()
    hit = client.search(query="skill")
    hit_ms = (time.perf_counter() - start_hit) * 1000.0
    assert len(hit) == 400

    # Primary correctness signal for cache path: remote index fetched only once.
    assert calls["count"] == 1
    # Keep a soft latency guard for cached lookup without asserting strict ordering,
    # which is noisy on shared CI/Windows runners.
    assert hit_ms < 500.0


def test_performance_query_path_with_sorting_under_500ms(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _build_index(index_path, total=3000)
    old = _set_index_env(index_path)
    try:
        client = TestClient(create_app())
        latencies_ms: list[float] = []
        for _ in range(30):
            started = time.perf_counter()
            response = client.get("/api/v1/skills", params={"sort_by": "downloads", "page_size": 100})
            latencies_ms.append((time.perf_counter() - started) * 1000.0)
            assert response.status_code == 200
            items = response.json()["items"]
            assert len(items) > 1
            first = items[0]["name"]
            second = items[1]["name"]
            assert first != second
        assert _p95_ms(latencies_ms) < 500.0
    finally:
        _restore_env(old)
