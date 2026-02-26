"""Unit and property tests for OwlHub read-only API routes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.api import create_app
from owlclaw.owlhub.api.routes.skills import _load_index


def _write_index(path: Path) -> None:
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 3,
        "skills": [
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "monitor entries",
                    "tags": ["trading", "monitor"],
                    "dependencies": {},
                },
                "version_state": "released",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "statistics": {"total_downloads": 10},
            },
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.1.0",
                    "description": "monitor entries",
                    "tags": ["trading", "monitor"],
                    "dependencies": {},
                },
                "version_state": "released",
                "updated_at": "2026-02-25T00:00:00+00:00",
                "statistics": {"total_downloads": 20},
            },
            {
                "manifest": {
                    "name": "risk-checker",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "risk checks",
                    "tags": ["risk"],
                    "dependencies": {},
                },
                "version_state": "deprecated",
                "updated_at": "2026-02-23T00:00:00+00:00",
                "statistics": {"total_downloads": 5},
            },
        ],
    }
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def test_read_only_endpoints(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path)
    monkeypatch.setenv("OWLHUB_INDEX_PATH", str(index_path))
    _load_index.cache_clear()

    app = create_app()
    client = TestClient(app)

    search = client.get("/api/v1/skills", params={"query": "entry", "tags": "trading", "sort_by": "downloads"})
    assert search.status_code == 200
    assert search.json()["total"] == 2
    assert search.json()["items"][0]["version"] == "1.1.0"

    detail = client.get("/api/v1/skills/acme/entry-monitor")
    assert detail.status_code == 200
    assert detail.json()["name"] == "entry-monitor"
    assert len(detail.json()["versions"]) == 2

    versions = client.get("/api/v1/skills/acme/entry-monitor/versions")
    assert versions.status_code == 200
    assert len(versions.json()) == 2


@settings(max_examples=40, deadline=None)
@given(
    count=st.integers(min_value=1, max_value=40),
    page=st.integers(min_value=1, max_value=8),
    page_size=st.integers(min_value=1, max_value=10),
)
def test_property_search_pagination(count: int, page: int, page_size: int) -> None:
    """Property: paginated API search returns non-overlapping subsets."""
    with tempfile.TemporaryDirectory() as workdir:
        skills = []
        for i in range(count):
            skills.append(
                {
                    "manifest": {
                        "name": f"skill-{i}",
                        "publisher": "acme",
                        "version": "1.0.0",
                        "description": "demo",
                        "tags": ["x"],
                        "dependencies": {},
                    },
                    "version_state": "released",
                    "updated_at": "2026-02-24T00:00:00+00:00",
                    "statistics": {"total_downloads": i},
                }
            )
        index_path = Path(workdir) / f"index-{count}.json"
        index_path.write_text(
            json.dumps(
                {"version": "1.0", "generated_at": "2026-02-24T00:00:00+00:00", "total_skills": count, "skills": skills}
            ),
            encoding="utf-8",
        )
        old = os.environ.get("OWLHUB_INDEX_PATH")
        os.environ["OWLHUB_INDEX_PATH"] = str(index_path)
        try:
            _load_index.cache_clear()
            client = TestClient(create_app())
            response = client.get("/api/v1/skills", params={"page": page, "page_size": page_size})
            assert response.status_code == 200
            payload = response.json()
            assert payload["total"] == count
            assert len(payload["items"]) <= page_size
            ids = [f"{item['publisher']}/{item['name']}@{item['version']}" for item in payload["items"]]
            assert len(ids) == len(set(ids))
        finally:
            _load_index.cache_clear()
            if old is None:
                os.environ.pop("OWLHUB_INDEX_PATH", None)
            else:
                os.environ["OWLHUB_INDEX_PATH"] = old
