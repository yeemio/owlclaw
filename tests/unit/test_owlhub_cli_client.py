"""Tests for OwlHub client and skill hub CLI commands."""

from __future__ import annotations

import io
import json
import tarfile
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from owlclaw.cli import _dispatch_skill_command
from owlclaw.cli.skill import skill_app
from owlclaw.owlhub import OwlHubClient
from owlclaw.owlhub.indexer import IndexBuilder

runner = CliRunner()


def _build_skill_archive(base: Path, *, name: str, publisher: str, version: str) -> Path:
    source_root = base / "src" / publisher / name
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / "SKILL.md").write_text(
        f"""---
name: "{name}"
description: "{name} description"
metadata:
  version: "{version}"
---
# {name}
""",
        encoding="utf-8",
    )
    archive_path = base / f"{name}-{version}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source_root.parent, arcname=f"{name}-{version}")
    return archive_path


def _build_index_file(
    base: Path,
    archive_path: Path,
    *,
    name: str,
    publisher: str,
    version: str,
    tags: list[str] | None = None,
) -> Path:
    checksum = IndexBuilder().calculate_checksum(archive_path)
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": name,
                    "publisher": publisher,
                    "version": version,
                    "description": f"{name} description",
                    "license": "MIT",
                    "tags": tags if tags is not None else ["demo"],
                    "dependencies": {},
                },
                "download_url": str(archive_path),
                "checksum": checksum,
                "published_at": "2026-02-24T00:00:00+00:00",
                "updated_at": "2026-02-24T00:00:00+00:00",
                "version_state": "released",
            }
        ],
    }
    index_file = base / "index.json"
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_file


def test_cli_search_install_and_installed_flow(tmp_path: Path, monkeypatch) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    _build_index_file(tmp_path, archive, name="entry-monitor", publisher="acme", version="1.0.0")
    monkeypatch.chdir(tmp_path)

    result_search = runner.invoke(
        skill_app,
        ["search"],
    )
    assert result_search.exit_code == 0
    assert "entry-monitor@1.0.0" in result_search.output
    assert "[demo]" in result_search.output

    result_install = runner.invoke(
        skill_app,
        ["install", "entry-monitor"],
    )
    assert result_install.exit_code == 0
    assert "Installed:" in result_install.output

    result_installed = runner.invoke(
        skill_app,
        ["installed"],
    )
    assert result_installed.exit_code == 0
    assert "entry-monitor@1.0.0" in result_installed.output


def test_cli_search_with_tag_mode_option(tmp_path: Path, monkeypatch, capsys) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    _build_index_file(
        tmp_path,
        archive,
        name="entry-monitor",
        publisher="acme",
        version="1.0.0",
        tags=["trading", "monitor"],
    )
    monkeypatch.chdir(tmp_path)
    handled = _dispatch_skill_command(["skill", "search", "--tags", "trading,missing", "--tag-mode", "or"])
    assert handled is True
    captured = capsys.readouterr()
    assert "entry-monitor@1.0.0" in captured.out


def test_install_rejects_checksum_mismatch(tmp_path: Path) -> None:
    archive = _build_skill_archive(tmp_path, name="bad-skill", publisher="acme", version="1.0.0")
    index_file = _build_index_file(tmp_path, archive, name="bad-skill", publisher="acme", version="1.0.0")
    data = json.loads(index_file.read_text(encoding="utf-8"))
    data["skills"][0]["checksum"] = "sha256:deadbeef"
    index_file.write_text(json.dumps(data), encoding="utf-8")

    client = OwlHubClient(index_url=str(index_file), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")
    try:
        client.install(name="bad-skill")
        raise AssertionError("expected checksum verification failure")
    except ValueError as exc:
        assert "checksum" in str(exc)


def test_tag_filter_supports_and_or(tmp_path: Path) -> None:
    archive = _build_skill_archive(tmp_path, name="entry-monitor", publisher="acme", version="1.0.0")
    _build_index_file(
        tmp_path,
        archive,
        name="entry-monitor",
        publisher="acme",
        version="1.0.0",
        tags=["trading", "monitor"],
    )
    client = OwlHubClient(index_url=str(tmp_path / "index.json"), install_dir=tmp_path / "skills", lock_file=tmp_path / "lock.json")
    and_results = client.search(query="entry", tags=["trading", "missing"], tag_mode="and")
    or_results = client.search(query="entry", tags=["trading", "missing"], tag_mode="or")
    assert len(and_results) == 0
    assert len(or_results) == 1


@settings(max_examples=100, deadline=None)
@given(
    query=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=0, max_size=8),
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8),
)
def test_property_6_multi_dimensional_search(query: str, name: str) -> None:
    """Property 6: search returns matching skills by keyword."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        archive = _build_skill_archive(root, name=name, publisher="acme", version="1.0.0")
        index_file = _build_index_file(root, archive, name=name, publisher="acme", version="1.0.0")
        client = OwlHubClient(index_url=str(index_file), install_dir=root / "skills", lock_file=root / "lock.json")
        results = client.search(query=query)
        if query and query not in f"{name} {name} description":
            assert all(query not in f"{item.name} {item.description}" for item in results)
        else:
            assert any(item.name == name for item in results)


@settings(max_examples=100, deadline=None)
@given(name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8))
def test_property_9_install_correctness(name: str) -> None:
    """Property 9: install creates local target and lock entry."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        archive = _build_skill_archive(root, name=name, publisher="acme", version="1.0.0")
        index_file = _build_index_file(root, archive, name=name, publisher="acme", version="1.0.0")
        lock_file = root / "skill-lock.json"
        client = OwlHubClient(index_url=str(index_file), install_dir=root / "skills", lock_file=lock_file)
        target = client.install(name=name)
        assert target.exists()
        installed = client.list_installed()
        assert any(item.get("name") == name for item in installed)


@settings(max_examples=100, deadline=None)
@given(name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8))
def test_property_11_lock_consistency(name: str) -> None:
    """Property 11: lock file reflects resolved installed version."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        archive = _build_skill_archive(root, name=name, publisher="acme", version="1.0.0")
        index_file = _build_index_file(root, archive, name=name, publisher="acme", version="1.0.0")
        lock_file = root / "skill-lock.json"
        client = OwlHubClient(index_url=str(index_file), install_dir=root / "skills", lock_file=lock_file)
        client.install(name=name)
        lock = json.loads(lock_file.read_text(encoding="utf-8"))
        assert lock["version"] == "1.0"
        assert any(item["name"] == name and item["version"] == "1.0.0" for item in lock["skills"])


@settings(max_examples=100, deadline=None)
@given(name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8))
def test_property_12_reject_invalid_package(name: str) -> None:
    """Property 12: invalid package without SKILL.md is rejected."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        bad_archive = root / f"{name}-1.0.0.tar.gz"
        with tarfile.open(bad_archive, "w:gz") as archive:
            payload = b"hello"
            info = tarfile.TarInfo(name=f"{name}/README.txt")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        index_file = _build_index_file(root, bad_archive, name=name, publisher="acme", version="1.0.0")
        client = OwlHubClient(index_url=str(index_file), install_dir=root / "skills", lock_file=root / "lock.json")
        try:
            client.install(name=name)
            raise AssertionError("expected missing SKILL.md failure")
        except ValueError as exc:
            assert "SKILL.md" in str(exc)


@settings(max_examples=100, deadline=None)
@given(
    tag_a=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6),
    tag_b=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6),
    query_tag=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6),
)
def test_property_21_tag_based_retrieval(tag_a: str, tag_b: str, query_tag: str) -> None:
    """Property 21: retrieval by tag matches tag membership."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        archive = _build_skill_archive(root, name="tag-skill", publisher="acme", version="1.0.0")
        tags = sorted({tag_a, tag_b})
        index_file = _build_index_file(root, archive, name="tag-skill", publisher="acme", version="1.0.0", tags=tags)
        client = OwlHubClient(index_url=str(index_file), install_dir=root / "skills", lock_file=root / "lock.json")
        results = client.search(query="tag", tags=[query_tag], tag_mode="or")
        if query_tag in tags:
            assert any(item.name == "tag-skill" for item in results)
        else:
            assert all(item.name != "tag-skill" for item in results)
