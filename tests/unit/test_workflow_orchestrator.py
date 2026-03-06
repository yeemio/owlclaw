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
    main_instruction = runtime_dir / "worktrees" / "main.md"
    review_instruction = runtime_dir / "worktrees" / "review.md"
    codex_mailbox = runtime_dir / "mailboxes" / "codex.json"

    assert snapshot_path.exists()
    assert actions_path.exists()
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
