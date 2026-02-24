"""Tests for OwlHub review system."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.review import ReviewStatus, ReviewSystem


def _create_valid_skill(path: Path, *, name: str, version: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"""---
name: "{name}"
description: "review test skill"
metadata:
  version: "{version}"
---
# {name}
""",
        encoding="utf-8",
    )


def test_submit_for_review_creates_record(tmp_path: Path) -> None:
    skill = tmp_path / "acme" / "entry"
    _create_valid_skill(skill, name="entry", version="1.0.0")
    system = ReviewSystem(storage_dir=tmp_path / "reviews")
    record = system.submit_for_review(skill_path=skill, skill_name="entry", version="1.0.0", publisher="acme")
    assert record.status == ReviewStatus.PENDING
    records = system.list_records()
    assert len(records) == 1
    assert records[0].review_id == "acme-entry-1.0.0"


def test_submit_invalid_skill_is_rejected(tmp_path: Path) -> None:
    broken = tmp_path / "acme" / "broken"
    broken.mkdir(parents=True)
    (broken / "README.md").write_text("missing skill file", encoding="utf-8")
    system = ReviewSystem(storage_dir=tmp_path / "reviews")
    record = system.submit_for_review(skill_path=broken, skill_name="broken", version="1.0.0", publisher="acme")
    assert record.status == ReviewStatus.REJECTED


def test_approve_and_reject_status_transitions(tmp_path: Path) -> None:
    skill = tmp_path / "acme" / "entry"
    _create_valid_skill(skill, name="entry", version="1.0.0")
    system = ReviewSystem(storage_dir=tmp_path / "reviews")
    submitted = system.submit_for_review(skill_path=skill, skill_name="entry", version="1.0.0", publisher="acme")
    approved = system.approve(review_id=submitted.review_id, reviewer="alice")
    assert approved.status == ReviewStatus.APPROVED
    try:
        system.reject(review_id=submitted.review_id, reviewer="bob", reason="late rejection")
        raise AssertionError("expected transition failure")
    except ValueError:
        pass


@settings(max_examples=100, deadline=None)
@given(
    should_approve=st.booleans(),
    reviewer=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6),
    reason=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=20),
)
def test_property_20_review_state_transitions(should_approve: bool, reviewer: str, reason: str) -> None:
    """Property 20: review status transitions remain valid."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        skill = root / "acme" / "entry"
        _create_valid_skill(skill, name="entry", version="1.0.0")
        system = ReviewSystem(storage_dir=root / "reviews")
        record = system.submit_for_review(skill_path=skill, skill_name="entry", version="1.0.0", publisher="acme")
        assert record.status == ReviewStatus.PENDING

        if should_approve:
            updated = system.approve(review_id=record.review_id, reviewer=reviewer)
            assert updated.status == ReviewStatus.APPROVED
        else:
            updated = system.reject(review_id=record.review_id, reviewer=reviewer, reason=reason)
            assert updated.status == ReviewStatus.REJECTED

        try:
            system.approve(review_id=record.review_id, reviewer=reviewer)
            raise AssertionError("expected second transition to fail")
        except ValueError:
            pass
