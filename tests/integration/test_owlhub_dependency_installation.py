"""Integration test for OwlHub dependency installation flow."""

from __future__ import annotations

import json
from pathlib import Path

from owlclaw.owlhub import OwlHubClient
from tests.unit.test_owlhub_cli_client import _build_index_file, _build_skill_archive


def test_install_with_dependencies_and_no_deps_flag(tmp_path: Path) -> None:
    dep_archive = _build_skill_archive(tmp_path, name="dep-skill", publisher="acme", version="1.0.0")
    root_archive = _build_skill_archive(tmp_path, name="root-skill", publisher="acme", version="1.0.0")
    _build_index_file(
        tmp_path,
        dep_archive,
        name="dep-skill",
        publisher="acme",
        version="1.0.0",
    )
    index_payload = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    root_checksum = json.loads(
        _build_index_file(
            tmp_path,
            root_archive,
            name="root-skill",
            publisher="acme",
            version="1.0.0",
            dependencies={"dep-skill": "^1.0.0"},
        ).read_text(encoding="utf-8")
    )["skills"][0]["checksum"]
    dep_entry = index_payload["skills"][0]
    root_entry = {
        "manifest": {
            "name": "root-skill",
            "publisher": "acme",
            "version": "1.0.0",
            "description": "root-skill description",
            "license": "MIT",
            "tags": ["demo"],
            "dependencies": {"dep-skill": "^1.0.0"},
        },
        "download_url": str(root_archive),
        "checksum": root_checksum,
        "published_at": "2026-02-24T00:00:00+00:00",
        "updated_at": "2026-02-24T00:00:00+00:00",
        "version_state": "released",
    }
    merged = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 2,
        "skills": [dep_entry, root_entry],
    }
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")
    client.install(name="root-skill")
    assert (tmp_path / "skills" / "dep-skill" / "1.0.0").exists()
    assert (tmp_path / "skills" / "root-skill" / "1.0.0").exists()

    client_no_deps = OwlHubClient(
        index_url=str(index_file),
        install_dir=tmp_path / "skills-no-deps",
        lock_file=tmp_path / "lock-no-deps.json",
    )
    client_no_deps.install(name="root-skill", no_deps=True)
    assert not (tmp_path / "skills-no-deps" / "dep-skill" / "1.0.0").exists()
    assert (tmp_path / "skills-no-deps" / "root-skill" / "1.0.0").exists()
