from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module(name: str, relative_path: str):
    path = Path(relative_path)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_create_object_validates_schema_and_indexes(tmp_path: Path) -> None:
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")

    created = objects.create_object(
        tmp_path,
        "finding",
        payload={
            "status": "new",
            "owner": "main",
            "title": "New finding",
            "summary": "Structured finding created by audit",
            "severity": "p1",
            "refs": {"spec": "workflow-closed-loop", "task": "2.2"},
            "relations": {"parent_delivery_id": "", "parent_verdict_id": ""},
        },
    )

    assert created["object_type"] == "finding"
    assert created["status"] == "new"

    index_path = tmp_path / ".kiro" / "runtime" / "findings" / "index.json"
    assert index_path.exists()
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_payload["total"] == 1
    assert index_payload["by_status"] == {"new": 1}


def test_update_object_status_moves_bucket_and_records_history(tmp_path: Path) -> None:
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")

    created = objects.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "pending",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["4.2"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce structured delivery"],
        },
    )

    updated = objects.update_object_status(
        tmp_path,
        "assignment",
        created["id"],
        new_status="claimed",
        actor="codex",
        reason="worker accepted assignment",
    )

    assert updated["status"] == "claimed"
    assert updated["history"][-1]["actor"] == "codex"
    assert updated["history"][-1]["from"] == "pending"
    assert updated["history"][-1]["to"] == "claimed"

    pending_path = tmp_path / ".kiro" / "runtime" / "assignments" / "pending" / f"{created['id']}.json"
    active_path = tmp_path / ".kiro" / "runtime" / "assignments" / "active" / f"{created['id']}.json"
    assert not pending_path.exists()
    assert active_path.exists()


def test_invalid_transition_is_rejected(tmp_path: Path) -> None:
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")

    created = objects.create_object(
        tmp_path,
        "review_verdict",
        payload={
            "status": "pending_main",
            "owner": "review",
            "delivery_id": "delivery-1",
            "verdict": "APPROVE",
            "new_finding_ids": [],
            "merge_ready": True,
            "notes": "ready",
        },
    )

    with pytest.raises(ValueError, match="illegal review_verdict state transition"):
        objects.update_object_status(
            tmp_path,
            "review_verdict",
            created["id"],
            new_status="pending_main",
            actor="main",
        )


def test_build_object_summary_counts_all_types(tmp_path: Path) -> None:
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")
    objects.ensure_object_dirs(tmp_path)
    objects.create_object(
        tmp_path,
        "blocker",
        payload={
            "status": "open",
            "owner": "main",
            "source_type": "assignment",
            "source_id": "assignment-1",
            "summary": "waiting for human decision",
        },
    )

    summary = objects.build_object_summary(tmp_path)
    assert summary["total_objects"] == 1
    assert summary["by_type"]["blocker"]["total"] == 1
    assert summary["by_type"]["blocker"]["by_status"] == {"open": 1}


def test_claim_and_stale_detection_for_assignment(tmp_path: Path) -> None:
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")
    created = objects.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "pending",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "audit-deep-remediation-followup",
            "task_refs": ["#47"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce structured delivery"],
            "claim": None,
        },
    )

    objects.claim_object(tmp_path, "assignment", created["id"], actor="codex", lease_seconds=1)
    stalled = objects.find_stale_objects(tmp_path, stale_seconds=0)

    assert stalled
    assert stalled[0]["object_type"] == "assignment"
