"""Unit and property tests for OwlHub index builder."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.indexer import IndexBuilder, SkillRepositoryCrawler
from owlclaw.owlhub.statistics import SkillStatistics


def _write_skill(root: Path, publisher: str, name: str, version: str, description: str) -> Path:
    skill_dir = root / publisher / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: "{name}"
description: {description}
metadata:
  version: "{version}"
---
# {name}
""",
        encoding="utf-8",
    )
    return skill_dir


def test_build_index_with_single_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "acme", "entry-monitor", "1.0.0", "Monitor entry opportunities.")
    builder = IndexBuilder(SkillRepositoryCrawler())
    index = builder.build_index([str(tmp_path)])
    assert index["version"] == "1.0"
    assert index["total_skills"] == 1
    assert index["skills"][0]["manifest"]["name"] == "entry-monitor"
    assert "search_index" in index


def test_build_index_includes_statistics(tmp_path: Path) -> None:
    class _StaticStatsTracker:
        def get_statistics(self, *, skill_name: str, publisher: str, repository: str | None = None) -> SkillStatistics:
            _ = (skill_name, publisher, repository)
            return SkillStatistics(
                skill_name="entry-monitor",
                publisher="acme",
                total_downloads=33,
                downloads_last_30d=7,
                total_installs=0,
                active_installs=0,
                last_updated=datetime(2026, 2, 24, 0, 0, tzinfo=timezone.utc),
            )

    _write_skill(tmp_path, "acme", "entry-monitor", "1.0.0", "Monitor entry opportunities.")
    builder = IndexBuilder(SkillRepositoryCrawler(), statistics_tracker=_StaticStatsTracker())
    index = builder.build_index([str(tmp_path)])
    statistics = index["skills"][0]["statistics"]
    assert statistics["total_downloads"] == 33
    assert statistics["downloads_last_30d"] == 7


def test_build_index_generates_search_metadata(tmp_path: Path) -> None:
    _write_skill(tmp_path, "acme", "entry-monitor", "1.0.0", "Monitor entry opportunities.")
    builder = IndexBuilder(SkillRepositoryCrawler())
    index = builder.build_index([str(tmp_path)])
    search_items = index["search_index"]
    assert len(search_items) == 1
    assert search_items[0]["id"] == "acme/entry-monitor@1.0.0"
    assert "monitor" in search_items[0]["search_text"]


def test_build_index_handles_invalid_skill_frontmatter(tmp_path: Path) -> None:
    broken = tmp_path / "acme" / "broken"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("# no frontmatter", encoding="utf-8")
    builder = IndexBuilder(SkillRepositoryCrawler())
    index = builder.build_index([str(tmp_path)])
    assert index["total_skills"] == 0


def test_build_index_backward_compatibility_keys(tmp_path: Path) -> None:
    _write_skill(tmp_path, "acme", "entry-monitor", "1.0.0", "Monitor entry opportunities.")
    index = IndexBuilder().build_index([str(tmp_path)])
    assert {"version", "generated_at", "total_skills", "skills"}.issubset(index.keys())


@settings(max_examples=100, deadline=None)
@given(
    publisher=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12),
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12),
    major=st.integers(min_value=0, max_value=9),
    minor=st.integers(min_value=0, max_value=9),
    patch=st.integers(min_value=0, max_value=9),
)
def test_property_1_publish_and_retrieve(
    publisher: str,
    name: str,
    major: int,
    minor: int,
    patch: int,
) -> None:
    """Property 1: published skill appears in generated index."""
    version = f"{major}.{minor}.{patch}"
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        _write_skill(root, publisher, name, version, "Valid description text.")
        index = IndexBuilder().build_index([str(root)])
        assert any(
            item["manifest"]["name"] == name and item["manifest"]["version"] == version for item in index["skills"]
        )


@settings(max_examples=100, deadline=None)
@given(
    values=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=9),
            st.integers(min_value=0, max_value=9),
            st.integers(min_value=0, max_value=9),
        ),
        min_size=2,
        max_size=5,
        unique=True,
    )
)
def test_property_3_version_history_immutability(values: list[tuple[int, int, int]]) -> None:
    """Property 3: multiple versions remain queryable in index output."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        versions = [f"{major}.{minor}.{patch}" for major, minor, patch in values]
        for version in versions:
            _write_skill(root / version.replace(".", "_"), "acme", "entry-monitor", version, "History test.")
        index = IndexBuilder().build_index([str(root)])
        indexed_versions = {item["manifest"]["version"] for item in index["skills"]}
        assert indexed_versions.issuperset(set(versions))


@settings(max_examples=100, deadline=None)
@given(payload=st.binary(min_size=1, max_size=128))
def test_property_16_checksum_integrity(payload: bytes) -> None:
    """Property 16: checksum stays stable for unchanged file content."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        file_path = root / "blob.bin"
        file_path.write_bytes(payload)
        builder = IndexBuilder()
        checksum_a = builder.calculate_checksum(file_path)
        checksum_b = builder.calculate_checksum(file_path)
        assert checksum_a == checksum_b
        assert checksum_a.startswith("sha256:")
