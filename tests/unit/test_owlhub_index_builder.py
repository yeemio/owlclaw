"""Unit and property tests for OwlHub index builder."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.indexer import IndexBuilder, SkillRepositoryCrawler


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


def test_build_index_handles_invalid_skill_frontmatter(tmp_path: Path) -> None:
    broken = tmp_path / "acme" / "broken"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("# no frontmatter", encoding="utf-8")
    builder = IndexBuilder(SkillRepositoryCrawler())
    index = builder.build_index([str(tmp_path)])
    assert index["total_skills"] == 0


@settings(max_examples=100)
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


@settings(max_examples=100)
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
