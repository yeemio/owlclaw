"""Tests for OwlHub statistics tracker."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.statistics import StatisticsTracker


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_get_statistics_fetches_github_downloads(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
    releases = [
        {
            "published_at": "2026-02-20T00:00:00Z",
            "assets": [{"download_count": 12}, {"download_count": 3}],
        },
        {
            "published_at": "2025-12-01T00:00:00Z",
            "assets": [{"download_count": 5}],
        },
    ]

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        assert request.full_url.endswith("/repos/acme/entry-monitor/releases")
        return _FakeResponse(json.dumps(releases))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tracker = StatisticsTracker(now_fn=lambda: now)
    stats = tracker.get_statistics(
        skill_name="entry-monitor",
        publisher="acme",
        repository="https://github.com/acme/entry-monitor",
    )

    assert stats.total_downloads == 20
    assert stats.downloads_last_30d == 15


def test_statistics_cache_reuses_previous_response(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
    calls = {"count": 0}
    releases = [{"published_at": "2026-02-20T00:00:00Z", "assets": [{"download_count": 10}]}]

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        _ = request
        calls["count"] += 1
        return _FakeResponse(json.dumps(releases))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tracker = StatisticsTracker(now_fn=lambda: now, cache_ttl_seconds=3600)
    first = tracker.get_statistics(skill_name="entry", publisher="acme", repository="https://github.com/acme/entry")
    second = tracker.get_statistics(skill_name="entry", publisher="acme", repository="https://github.com/acme/entry")

    assert first.total_downloads == 10
    assert second.total_downloads == 10
    assert calls["count"] == 1


def test_get_statistics_handles_rate_limit(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)

    def fake_urlopen(request: Request, timeout: int):  # noqa: ARG001
        raise HTTPError(request.full_url, 403, "rate limited", hdrs=None, fp=None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    tracker = StatisticsTracker(now_fn=lambda: now)

    stats = tracker.get_statistics(skill_name="entry", publisher="acme", repository="https://github.com/acme/entry")
    assert stats.total_downloads == 0
    assert stats.downloads_last_30d == 0


def test_get_statistics_skips_non_github_local_like_repository(monkeypatch) -> None:
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)

    def fail_if_called(request: Request, timeout: int):  # noqa: ARG001
        raise AssertionError("urlopen should not be called for non-GitHub local-like repository")

    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)
    tracker = StatisticsTracker(now_fn=lambda: now)
    stats = tracker.get_statistics(skill_name="entry", publisher="acme", repository="templates/skills")
    assert stats.total_downloads == 0
    assert stats.downloads_last_30d == 0


def test_statistics_aggregation_for_local_events() -> None:
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
    tracker = StatisticsTracker(now_fn=lambda: now)

    tracker.record_download(skill_name="entry", publisher="acme", version="1.0.0", occurred_at=now - timedelta(days=5))
    tracker.record_download(
        skill_name="entry",
        publisher="acme",
        version="1.0.0",
        occurred_at=now - timedelta(days=45),
    )
    tracker.record_install(
        skill_name="entry",
        publisher="acme",
        version="1.0.0",
        user_id="u1",
        occurred_at=now - timedelta(days=1),
    )
    tracker.record_install(
        skill_name="entry",
        publisher="acme",
        version="1.0.0",
        user_id="u2",
        occurred_at=now - timedelta(days=40),
    )
    tracker.record_install(
        skill_name="entry",
        publisher="acme",
        version="1.0.0",
        user_id="u1",
        occurred_at=now - timedelta(days=2),
    )

    stats = tracker.get_statistics(skill_name="entry", publisher="acme")
    assert stats.total_downloads == 2
    assert stats.downloads_last_30d == 1
    assert stats.total_installs == 3
    assert stats.active_installs == 1


@settings(max_examples=10, deadline=None)
@given(
    download_offsets=st.lists(st.integers(min_value=-60, max_value=0), min_size=0, max_size=80),
    install_events=st.lists(
        st.tuples(
            st.text(alphabet="abc123", min_size=1, max_size=4),
            st.integers(min_value=-60, max_value=0),
        ),
        min_size=0,
        max_size=80,
    ),
)
def test_property_18_statistics_count_accuracy(
    download_offsets: list[int],
    install_events: list[tuple[str, int]],
) -> None:
    """Property 18: operation counts match aggregated statistics."""
    now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
    tracker = StatisticsTracker(now_fn=lambda: now)
    for offset in download_offsets:
        tracker.record_download(
            skill_name="entry",
            publisher="acme",
            version="1.0.0",
            occurred_at=now + timedelta(days=offset),
        )
    for user_id, offset in install_events:
        tracker.record_install(
            skill_name="entry",
            publisher="acme",
            version="1.0.0",
            user_id=user_id,
            occurred_at=now + timedelta(days=offset),
        )

    stats = tracker.get_statistics(skill_name="entry", publisher="acme")
    expected_downloads_30d = sum(1 for offset in download_offsets if offset >= -30)
    expected_active_users = {user_id for user_id, offset in install_events if offset >= -30}

    assert stats.total_downloads == len(download_offsets)
    assert stats.downloads_last_30d == expected_downloads_30d
    assert stats.total_installs == len(install_events)
    assert stats.active_installs == len(expected_active_users)

