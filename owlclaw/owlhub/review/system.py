"""Review system for OwlHub Phase 2."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from owlclaw.owlhub.validator import Validator


class ReviewStatus(str, Enum):
    """Review status lifecycle."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ReviewRecord:
    """One review record."""

    review_id: str
    skill_name: str
    version: str
    publisher: str
    status: ReviewStatus
    comments: str
    reviewed_at: str


class ReviewSystem:
    """Store and update review records with automated validation checks."""

    def __init__(self, *, storage_dir: Path, validator: Validator | None = None) -> None:
        self.storage_dir = storage_dir
        self.validator = validator or Validator()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def submit_for_review(self, *, skill_path: Path, skill_name: str, version: str, publisher: str) -> ReviewRecord:
        """Submit one skill for automated validation and review."""
        structure_result = self.validator.validate_structure(skill_path)
        if not structure_result.is_valid:
            comments = "; ".join(error.message for error in structure_result.errors) or "structure validation failed"
            record = self._build_record(
                skill_name=skill_name,
                version=version,
                publisher=publisher,
                status=ReviewStatus.REJECTED,
                comments=comments,
            )
            self._write_record(record)
            return record

        record = self._build_record(
            skill_name=skill_name,
            version=version,
            publisher=publisher,
            status=ReviewStatus.PENDING,
            comments="automated validation passed",
        )
        self._write_record(record)
        return record

    def approve(self, *, review_id: str, reviewer: str, comments: str = "") -> ReviewRecord:
        """Approve one pending review record."""
        current = self._read_record(review_id)
        if current.status != ReviewStatus.PENDING:
            raise ValueError("only pending review can be approved")
        approved = ReviewRecord(
            review_id=current.review_id,
            skill_name=current.skill_name,
            version=current.version,
            publisher=current.publisher,
            status=ReviewStatus.APPROVED,
            comments=(comments or "approved").strip() + f" by {reviewer}",
            reviewed_at=_utc_now(),
        )
        self._write_record(approved)
        return approved

    def reject(self, *, review_id: str, reviewer: str, reason: str) -> ReviewRecord:
        """Reject one pending review record."""
        current = self._read_record(review_id)
        if current.status != ReviewStatus.PENDING:
            raise ValueError("only pending review can be rejected")
        rejected = ReviewRecord(
            review_id=current.review_id,
            skill_name=current.skill_name,
            version=current.version,
            publisher=current.publisher,
            status=ReviewStatus.REJECTED,
            comments=f"{reason.strip()} by {reviewer}",
            reviewed_at=_utc_now(),
        )
        self._write_record(rejected)
        return rejected

    def list_records(self) -> list[ReviewRecord]:
        """List stored review records sorted by reviewed_at descending."""
        records: list[ReviewRecord] = []
        for file_path in sorted(self.storage_dir.glob("*.json")):
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            records.append(_record_from_dict(payload))
        records.sort(key=lambda item: item.reviewed_at, reverse=True)
        return records

    def _build_record(
        self,
        *,
        skill_name: str,
        version: str,
        publisher: str,
        status: ReviewStatus,
        comments: str,
    ) -> ReviewRecord:
        review_id = f"{publisher}-{skill_name}-{version}"
        return ReviewRecord(
            review_id=review_id,
            skill_name=skill_name,
            version=version,
            publisher=publisher,
            status=status,
            comments=comments,
            reviewed_at=_utc_now(),
        )

    def _read_record(self, review_id: str) -> ReviewRecord:
        file_path = self.storage_dir / f"{review_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"review not found: {review_id}")
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return _record_from_dict(payload)

    def _write_record(self, record: ReviewRecord) -> None:
        file_path = self.storage_dir / f"{record.review_id}.json"
        file_path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")


def _record_from_dict(payload: dict[str, str]) -> ReviewRecord:
    return ReviewRecord(
        review_id=str(payload.get("review_id", "")),
        skill_name=str(payload.get("skill_name", "")),
        version=str(payload.get("version", "")),
        publisher=str(payload.get("publisher", "")),
        status=ReviewStatus(str(payload.get("status", ReviewStatus.PENDING.value))),
        comments=str(payload.get("comments", "")),
        reviewed_at=str(payload.get("reviewed_at", "")),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
