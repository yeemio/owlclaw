"""Integration test for OwlHub Phase 1 publish/search/install flow."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.indexer import IndexBuilder
from owlclaw.owlhub.validator import Validator


def _create_skill_repo(root: Path, publisher: str, skill_name: str, version: str) -> Path:
    repo = root / publisher / skill_name
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "SKILL.md").write_text(
        f"""---
name: "{skill_name}"
description: "Phase1 integration skill"
metadata:
  version: "{version}"
---
# {skill_name}
""",
        encoding="utf-8",
    )
    return repo


def _archive_repo(root: Path, repo: Path) -> Path:
    archive = root / f"{repo.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(repo, arcname=repo.name)
    return archive


def test_phase1_publish_search_install_flow(tmp_path: Path) -> None:
    """Property 25: static index generated locally is accessible by CLI client."""
    repo = _create_skill_repo(tmp_path / "repos", "acme", "phase1-monitor", "1.0.0")
    validator = Validator()
    assert validator.validate_structure(repo).is_valid is True

    archive = _archive_repo(tmp_path, repo)
    checksum = IndexBuilder().calculate_checksum(archive)
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": "phase1-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "Phase1 integration skill",
                    "license": "MIT",
                    "tags": ["phase1"],
                    "dependencies": {},
                },
                "download_url": str(archive),
                "checksum": checksum,
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "version_state": "released",
            }
        ],
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    client = OwlHubClient(
        index_url=str(index_path),
        install_dir=tmp_path / ".owlhub" / "skills",
        lock_file=tmp_path / "skill-lock.json",
    )
    search_results = client.search(query="phase1")
    assert len(search_results) == 1
    assert search_results[0].name == "phase1-monitor"

    install_path = client.install(name="phase1-monitor")
    assert install_path.exists()
    installed = client.list_installed()
    assert len(installed) == 1
    assert installed[0]["name"] == "phase1-monitor"

