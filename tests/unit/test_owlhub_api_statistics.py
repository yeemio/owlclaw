"""Unit and property tests for OwlHub statistics API and tracker persistence."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index
from owlclaw.owlhub.statistics import StatisticsTracker


def _issue_token(client: TestClient, *, code: str, role: str = "publisher") -> str:
    response = client.post("/api/v1/auth/token", json={"github_code": code, "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def _prepare_env(root: Path) -> dict[str, str | None]:
    old = {key: os.getenv(key) for key in ("OWLHUB_INDEX_PATH", "OWLHUB_STATISTICS_DB")}
    index_payload = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "Entry monitor",
                    "license": "MIT",
                    "dependencies": {},
                    "tags": [],
                },
                "version_state": "released",
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "statistics": {"total_downloads": 0, "downloads_last_30d": 0},
            }
        ],
    }
    index_path = root / "index.json"
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False), encoding="utf-8")
    os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
    os.environ["OWLHUB_STATISTICS_DB"] = str(root / "skill_statistics.json")
    _load_index.cache_clear()
    return old


def _restore_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    _load_index.cache_clear()


def test_statistics_endpoint_and_export_formats(tmp_path: Path) -> None:
    old = _prepare_env(tmp_path)
    try:
        app = create_app()
        tracker = app.state.statistics_tracker
        now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
        tracker.record_download(
            skill_name="entry-monitor",
            publisher="acme",
            version="1.0.0",
            occurred_at=now - timedelta(days=3),
        )
        tracker.record_install(
            skill_name="entry-monitor",
            publisher="acme",
            version="1.0.0",
            user_id="u1",
            occurred_at=now - timedelta(days=2),
        )
        client = TestClient(app)

        stats = client.get("/api/v1/skills/acme/entry-monitor/statistics")
        assert stats.status_code == 200
        assert stats.json()["total_downloads"] == 1
        assert stats.json()["total_installs"] == 1

        publisher_token = _issue_token(client, code="gho_acme1234", role="publisher")
        forbidden = client.get(
            "/api/v1/statistics/export",
            params={"format": "json"},
            headers={"Authorization": f"Bearer {publisher_token}"},
        )
        assert forbidden.status_code == 403

        admin_token = _issue_token(client, code="gho_admin1234", role="admin")
        json_export = client.get(
            "/api/v1/statistics/export",
            params={"format": "json"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert json_export.status_code == 200
        assert json_export.json()[0]["skill_name"] == "entry-monitor"

        csv_export = client.get(
            "/api/v1/statistics/export",
            params={"format": "csv"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert csv_export.status_code == 200
        assert "text/csv" in csv_export.headers["content-type"]
        assert "skill_name" in csv_export.text

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert 'owlhub_skill_downloads_total{publisher="acme",skill="entry-monitor"} 1' in metrics.text
        assert 'owlhub_skill_installs_total{publisher="acme",skill="entry-monitor"} 1' in metrics.text
    finally:
        _restore_env(old)


def test_statistics_tracker_concurrent_recording(tmp_path: Path) -> None:
    tracker = StatisticsTracker(storage_path=tmp_path / "stats.json")

    def worker(idx: int) -> None:
        tracker.record_download(skill_name="entry", publisher="acme", version="1.0.0")
        tracker.record_install(skill_name="entry", publisher="acme", version="1.0.0", user_id=f"u{idx % 5}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        for i in range(120):
            pool.submit(worker, i)

    stats = tracker.get_statistics(skill_name="entry", publisher="acme")
    assert stats.total_downloads == 120
    assert stats.total_installs == 120
    assert stats.active_installs == 5


@settings(max_examples=100, deadline=None)
@given(
    download_count=st.integers(min_value=0, max_value=120),
    install_users=st.lists(st.text(alphabet="abc123", min_size=1, max_size=4), min_size=0, max_size=120),
)
def test_property_18_statistics_count_accuracy_database_version(
    download_count: int,
    install_users: list[str],
) -> None:
    """Property 18: database-backed event counts stay accurate."""
    with tempfile.TemporaryDirectory() as workdir:
        now = datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc)
        tracker = StatisticsTracker(storage_path=Path(workdir) / "stats.json", now_fn=lambda: now)
        for _ in range(download_count):
            tracker.record_download(skill_name="entry", publisher="acme", version="1.0.0")
        for user_id in install_users:
            tracker.record_install(skill_name="entry", publisher="acme", version="1.0.0", user_id=user_id)
        tracker.run_daily_aggregation()
        stats = tracker.get_statistics(skill_name="entry", publisher="acme")
        assert stats.total_downloads == download_count
        assert stats.total_installs == len(install_users)
        assert stats.active_installs == len(set(install_users))


@settings(max_examples=80, deadline=None)
@given(
    skills=st.lists(
        st.tuples(
            st.sampled_from(["acme", "owl", "team"]),
            st.sampled_from(["entry", "risk", "alpha"]),
            st.integers(min_value=0, max_value=20),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_property_19_statistics_export_completeness(skills: list[tuple[str, str, int]]) -> None:
    """Property 19: JSON/CSV exports are complete and schema-consistent."""
    with tempfile.TemporaryDirectory() as workdir:
        tracker = StatisticsTracker(storage_path=Path(workdir) / "stats.json")
        expected_keys: set[tuple[str, str]] = set()
        for publisher, skill_name, count in skills:
            if count > 0:
                expected_keys.add((publisher, skill_name))
            for idx in range(count):
                tracker.record_download(skill_name=skill_name, publisher=publisher, version="1.0.0")
                tracker.record_install(
                    skill_name=skill_name,
                    publisher=publisher,
                    version="1.0.0",
                    user_id=f"user-{idx % 5}",
                )

        json_rows = json.loads(tracker.export(format="json"))
        json_keys = {(row["publisher"], row["skill_name"]) for row in json_rows}
        assert expected_keys.issubset(json_keys)

        csv_rows = list(csv.DictReader(StringIO(tracker.export(format="csv"))))
        csv_keys = {(row["publisher"], row["skill_name"]) for row in csv_rows}
        assert expected_keys.issubset(csv_keys)
        for row in csv_rows:
            assert "total_downloads" in row
            assert "downloads_last_30d" in row
            assert "total_installs" in row
            assert "active_installs" in row
