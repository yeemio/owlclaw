from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module(name: str, relative_path: str):
    path = Path(relative_path)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_write_runtime_files_creates_snapshot_and_instructions(tmp_path: Path) -> None:
    status_module = _load_module("workflow_status", "scripts/workflow_status.py")
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    orchestrator_module = _load_module("workflow_orchestrator", "scripts/workflow_orchestrator.py")

    objects_module.create_object(
        tmp_path,
        "blocker",
        payload={
            "status": "open",
            "owner": "main",
            "source_type": "runtime",
            "source_id": "workflow-1",
            "summary": "Example blocker for object statistics",
        },
    )

    snapshot = status_module.WorkflowSnapshot(
        repo_root=str(tmp_path),
        audit=status_module.AuditSummary(
            total_findings=44,
            p1=2,
            low=42,
            spec_progress="7/29",
            spec_status="进行中（7/29）",
            spec_summary="待审代码提交已形成",
        ),
        worktrees=[
            status_module.WorktreeState("main", "main", str(tmp_path), "orchestrator", True, [], 0, 0, []),
            status_module.WorktreeState(
                "review",
                "review-work",
                str(tmp_path / "review"),
                "review",
                True,
                [],
                0,
                0,
                [],
            ),
            status_module.WorktreeState(
                "codex",
                "codex-work",
                str(tmp_path / "codex"),
                "coding",
                True,
                [],
                2,
                0,
                ["abc fix"],
            ),
            status_module.WorktreeState(
                "codex-gpt",
                "codex-gpt-work",
                str(tmp_path / "codex-gpt"),
                "coding",
                True,
                [],
                0,
                0,
                [],
            ),
        ],
        next_action="review-work should review pending coding branches: codex-work",
        blockers=[],
    )

    orchestrator_module.write_runtime_files(tmp_path, snapshot)

    runtime_dir = tmp_path / ".kiro" / "runtime"
    snapshot_path = runtime_dir / "workflow_snapshot.json"
    actions_path = runtime_dir / "workflow_actions.md"
    objects_path = runtime_dir / "workflow_objects.md"
    blockers_path = runtime_dir / "workflow_blockers.md"
    main_instruction = runtime_dir / "worktrees" / "main.md"
    review_instruction = runtime_dir / "worktrees" / "review.md"
    codex_mailbox = runtime_dir / "mailboxes" / "codex.json"

    assert snapshot_path.exists()
    assert actions_path.exists()
    assert objects_path.exists()
    assert blockers_path.exists()
    assert main_instruction.exists()
    assert review_instruction.exists()
    assert codex_mailbox.exists()

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["action"]["stage"] == "review"
    assert payload["action"]["owner"] == "review"
    assert payload["action"]["pending_coding_branches"] == ["codex-work"]
    assert payload["acks"] == {
        "codex": None,
        "codex-gpt": None,
        "main": None,
        "review": None,
    }
    assert payload["objects"]["total_objects"] == 1
    assert payload["objects"]["by_type"]["blocker"]["by_status"] == {"open": 1}

    actions_text = actions_path.read_text(encoding="utf-8")
    assert "Review `codex-work` pending commits" in actions_text

    review_text = review_instruction.read_text(encoding="utf-8")
    assert "Action: review coding branches in order:" in review_text

    mailbox_payload = json.loads(codex_mailbox.read_text(encoding="utf-8"))
    assert mailbox_payload["agent"] == "codex"
    assert mailbox_payload["action"] == "wait_for_review"
    assert mailbox_payload["priority"] == "high"
    assert mailbox_payload["pending_commits"] == ["abc fix"]

    review_mailbox = json.loads((runtime_dir / "mailboxes" / "review.json").read_text(encoding="utf-8"))
    assert review_mailbox["pending_commits"] == ["abc fix"]
    assert (runtime_dir / "findings" / "open").exists()
    assert (runtime_dir / "assignments" / "pending").exists()
    assert "## blocker" in objects_path.read_text(encoding="utf-8")
    assert "total_open: 1" in blockers_path.read_text(encoding="utf-8")


def test_write_runtime_files_promotes_assignment_only_after_queues_clear(tmp_path: Path) -> None:
    status_module = _load_module("workflow_status", "scripts/workflow_status.py")
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    orchestrator_module = _load_module("workflow_orchestrator", "scripts/workflow_orchestrator.py")

    snapshot = status_module.WorkflowSnapshot(
        repo_root=str(tmp_path),
        audit=status_module.AuditSummary(
            total_findings=44,
            p1=2,
            low=42,
            spec_progress="7/29",
            spec_status="进行中（7/29）",
            spec_summary="待审代码提交已形成",
        ),
        worktrees=[
            status_module.WorktreeState("main", "main", str(tmp_path), "orchestrator", True, [], 0, 0, []),
            status_module.WorktreeState(
                "review",
                "review-work",
                str(tmp_path / "review"),
                "review",
                True,
                [],
                0,
                0,
                [],
            ),
            status_module.WorktreeState(
                "codex",
                "codex-work",
                str(tmp_path / "codex"),
                "coding",
                True,
                [],
                0,
                0,
                [],
            ),
            status_module.WorktreeState(
                "codex-gpt",
                "codex-gpt-work",
                str(tmp_path / "codex-gpt"),
                "coding",
                True,
                [],
                0,
                0,
                [],
            ),
        ],
        next_action="workflow stable: no pending review or merge action",
        blockers=[],
    )

    orchestrator_module.write_runtime_files(tmp_path, snapshot)

    payload = json.loads((tmp_path / ".kiro" / "runtime" / "workflow_snapshot.json").read_text(encoding="utf-8"))
    assert payload["action"]["stage"] == "assign"
    assert payload["action"]["owner"] == "main"

    main_mailbox = json.loads((tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").read_text(encoding="utf-8"))
    assert main_mailbox["action"] == "assign_next_batch"
    assert main_mailbox["next_expected_transition"] == "assign_next_batch"
    assert main_mailbox["summary"] == "Coding and review queues are clear; assign the next batch before nudging agents."


def test_write_runtime_files_creates_triage_for_new_findings_and_links_main_mailbox(tmp_path: Path) -> None:
    status_module = _load_module("workflow_status", "scripts/workflow_status.py")
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    orchestrator_module = _load_module("workflow_orchestrator", "scripts/workflow_orchestrator.py")

    created_finding = objects_module.create_object(
        tmp_path,
        "finding",
        payload={
            "status": "new",
            "owner": "main",
            "source": "audit-a",
            "source_type": "audit",
            "title": "Audit finding",
            "summary": "New audit issue waiting for triage",
            "severity": "p1",
            "refs": {"spec": "workflow-closed-loop", "task_ref": "2.2"},
            "relations": {"parent_delivery_id": "", "parent_verdict_id": ""},
            "proposed_assignment": {"target_agent": "codex", "target_branch": "codex-work"},
            "audit_metadata": {
                "profile": "deep_audit",
                "files": ["owlclaw/agent/runtime/runtime.py"],
                "dimensions": ["core_logic"],
                "thinking_lenses": ["failure"],
                "evidence": "Traced runtime path directly from code.",
                "code_changes_allowed": False,
            },
        },
    )

    snapshot = status_module.WorkflowSnapshot(
        repo_root=str(tmp_path),
        audit=status_module.AuditSummary(
            total_findings=1,
            p1=1,
            low=0,
            spec_progress="0/11",
            spec_status="进行中（0/11）",
            spec_summary="workflow-closed-loop waiting for implementation",
        ),
        worktrees=[
            status_module.WorktreeState("main", "main", str(tmp_path), "orchestrator", True, [], 0, 0, []),
            status_module.WorktreeState("review", "review-work", str(tmp_path / "review"), "review", True, [], 0, 0, []),
            status_module.WorktreeState("codex", "codex-work", str(tmp_path / "codex"), "coding", True, [], 0, 0, []),
            status_module.WorktreeState("codex-gpt", "codex-gpt-work", str(tmp_path / "codex-gpt"), "coding", True, [], 0, 0, []),
        ],
        next_action="workflow stable: no pending review or merge action",
        blockers=[],
    )

    orchestrator_module.write_runtime_files(tmp_path, snapshot)

    triage_items = objects_module.list_objects(tmp_path, "triage_decision")
    assert len(triage_items) == 1
    assert triage_items[0]["finding_ids"] == [created_finding["id"]]
    assert triage_items[0]["status"] == "pending"

    main_mailbox = json.loads((tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").read_text(encoding="utf-8"))
    assert main_mailbox["object_type"] == "triage_decision"
    assert main_mailbox["object_id"] == triage_items[0]["id"]
    assert main_mailbox["summary"] == "Structured findings are waiting for triage and assignment."
