"""Integration test for OwlHub Phase 2 end-to-end flows."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.indexer import IndexBuilder
from owlclaw.owlhub.site import SiteGenerator


def _create_skill(root: Path, *, publisher: str, name: str, version: str, state: str = "released") -> Path:
    skill = root / publisher / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        f"""---
name: "{name}"
description: "Phase2 integration skill"
metadata:
  version: "{version}"
  state: "{state}"
---
# {name}
""",
        encoding="utf-8",
    )
    return skill


def _pack_skill(root: Path, skill: Path) -> Path:
    archive = root / f"{skill.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(skill, arcname=skill.name)
    return archive


def test_phase2_site_generation_and_cli_compatibility(tmp_path: Path) -> None:
    repo_root = tmp_path / "repos"
    _create_skill(repo_root, publisher="acme", name="phase2-monitor", version="1.0.0")
    _create_skill(repo_root, publisher="acme", name="phase2-monitor", version="1.1.0")

    archive = _pack_skill(tmp_path, repo_root / "acme" / "phase2-monitor")
    checksum = IndexBuilder().calculate_checksum(archive)
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 2,
        "skills": [
            {
                "manifest": {
                    "name": "phase2-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "Phase2 integration skill",
                    "license": "MIT",
                    "tags": ["phase2", "monitor"],
                    "dependencies": {},
                },
                "download_url": str(archive),
                "checksum": checksum,
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "version_state": "released",
                "statistics": {"total_downloads": 10, "downloads_last_30d": 6},
            },
            {
                "manifest": {
                    "name": "phase2-monitor",
                    "publisher": "acme",
                    "version": "1.1.0",
                    "description": "Phase2 integration skill",
                    "license": "MIT",
                    "tags": ["phase2", "monitor"],
                    "dependencies": {},
                },
                "download_url": str(archive),
                "checksum": checksum,
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "version_state": "released",
                "statistics": {"total_downloads": 12, "downloads_last_30d": 7},
            },
        ],
        "search_index": [
            {
                "id": "acme/phase2-monitor@1.0.0",
                "name": "phase2-monitor",
                "publisher": "acme",
                "version": "1.0.0",
                "tags": ["phase2", "monitor"],
                "search_text": "phase2-monitor phase2 integration skill phase2 monitor",
            },
            {
                "id": "acme/phase2-monitor@1.1.0",
                "name": "phase2-monitor",
                "publisher": "acme",
                "version": "1.1.0",
                "tags": ["phase2", "monitor"],
                "search_text": "phase2-monitor phase2 integration skill phase2 monitor",
            },
        ],
    }

    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    site_dir = tmp_path / "site"
    SiteGenerator().generate(index_data=index, output_dir=site_dir, base_url="https://owlhub.example")
    assert (site_dir / "index.html").exists()
    assert (site_dir / "dashboard.html").exists()
    assert (site_dir / "sitemap.xml").exists()
    assert (site_dir / "search-index.json").exists()

    client = OwlHubClient(
        index_url=str(index_path),
        install_dir=tmp_path / ".owlhub" / "skills",
        lock_file=tmp_path / "skill-lock.json",
    )
    results = client.search(query="phase2")
    assert len(results) == 2
    installed_path = client.install(name="phase2-monitor")
    assert installed_path.exists()
    installed = client.list_installed()
    assert installed[0]["version"] == "1.1.0"
