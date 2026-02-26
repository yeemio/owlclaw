"""Unit and property tests for OwlHub schema models."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.schema import IndexEntry, SkillManifest, VersionState
from owlclaw.owlhub.schema.models import utc_now


def test_utc_now_is_timezone_aware() -> None:
    current = utc_now()
    assert current.tzinfo is not None
    assert current.tzinfo == timezone.utc


@settings(max_examples=40, deadline=None)
@given(
    name=st.from_regex(r"^[a-z0-9]+(-[a-z0-9]+)*$", fullmatch=True),
    version=st.from_regex(r"^\d+\.\d+\.\d+$", fullmatch=True),
    publisher=st.from_regex(r"^[a-z0-9]+(-[a-z0-9]+)*$", fullmatch=True),
    description=st.text(min_size=10, max_size=80),
    license_name=st.sampled_from(["MIT", "Apache-2.0", "BSD-3-Clause"]),
    tags=st.lists(st.text(min_size=1, max_size=12), max_size=5),
    dependencies=st.dictionaries(
        keys=st.from_regex(r"^[a-z0-9]+(-[a-z0-9]+)*$", fullmatch=True),
        values=st.from_regex(r"^\^?\d+\.\d+\.\d+$", fullmatch=True),
        max_size=5,
    ),
    state=st.sampled_from([VersionState.DRAFT, VersionState.RELEASED, VersionState.DEPRECATED]),
)
def test_property_24_index_entry_json_serialization(
    name: str,
    version: str,
    publisher: str,
    description: str,
    license_name: str,
    tags: list[str],
    dependencies: dict[str, str],
    state: VersionState,
) -> None:
    """Property 24: GitHub index JSON format stays schema-compatible."""
    manifest = SkillManifest(
        name=name,
        version=version,
        publisher=publisher,
        description=description,
        license=license_name,
        tags=tags,
        dependencies=dependencies,
    )
    entry = IndexEntry(
        manifest=manifest,
        download_url=f"https://example.com/{publisher}/{name}/{version}.tar.gz",
        checksum="sha256:abc123",
        published_at=utc_now(),
        updated_at=utc_now(),
        version_state=state,
    )
    payload = asdict(entry)
    serialized = json.dumps(payload, default=str, ensure_ascii=False)
    decoded = json.loads(serialized)

    assert "manifest" in decoded
    assert decoded["manifest"]["name"] == name
    assert decoded["manifest"]["version"] == version
    assert decoded["manifest"]["publisher"] == publisher
    assert decoded["download_url"].startswith("https://")
    assert decoded["checksum"].startswith("sha256:")
    assert decoded["version_state"] in {"draft", "released", "deprecated"}

