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


def _write_assignments_md(repo_root: Path, *, include_spec: str = "workflow-closed-loop") -> None:
    path = repo_root / ".kiro" / "WORKTREE_ASSIGNMENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# Worktree 任务分配

### owlclaw-codex（编码 1）

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-codex\\` |
| 分支 | `codex-work` |
| 角色 | 编码：功能实现 + 测试 |
| 工作状态 | `WORKING` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **{include_spec}** | ✅ 1/1 | `scripts/` |

### codex-work 分配（当前批次）

| Spec | Phase | Task | Finding | 优先级 | 状态 |
|------|-------|------|---------|--------|------|
| **{include_spec}** | Phase 16 | #47 | Runtime | Low | 🟡 进行中 |

### owlclaw-codex-gpt（编码 2）

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-codex-gpt\\` |
| 分支 | `codex-gpt-work` |
| 角色 | 编码：功能实现 + 测试 |
| 工作状态 | `DONE` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **other-spec** | ✅ 1/1 | `scripts/` |

### codex-gpt-work 分配（当前批次）

| Spec | Phase | Task | Finding | 优先级 | 状态 |
|------|-------|------|---------|--------|------|
| **other-spec** | Phase 16 | #45 | Runtime | Low | 🟢 已完成 |

## 跨 Spec 依赖提示
""",
        encoding="utf-8",
    )


def test_process_once_runs_review_execution(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    invoked: dict[str, object] = {}

    def fake_invoke(repo_root: Path, agent: str, *, workdir: Path, prompt: str, timeout_seconds: int = 120) -> dict[str, object]:
        invoked["agent"] = agent
        invoked["workdir"] = str(workdir)
        invoked["prompt"] = prompt
        invoked["timeout_seconds"] = timeout_seconds
        return {
            "agent": agent,
            "runner": "claude",
            "executed_at": "2026-03-06T00:00:01+00:00",
            "workdir": str(workdir),
            "command": ["codex", "exec"],
            "returncode": 0,
            "last_message_path": str(tmp_path / "last.txt"),
            "log_path": str(tmp_path / "log.txt"),
            "last_message": "review complete",
            "error_kind": "",
        }

    executor_module._invoke_runner = fake_invoke
    result = executor_module.process_once(tmp_path, "review")

    assert result["status"] == "done"
    assert result["executed"] is True
    assert invoked["agent"] == "review"
    assert invoked["timeout_seconds"] == executor_module.LONG_RUNNING_TIMEOUT_SECONDS
    assert "你的岗位是代码审校门" in str(invoked["prompt"])
    assert "只审 codex-work 和 codex-gpt-work 的代码提交" in str(invoked["prompt"])

    ack = mailbox_module.read_ack(tmp_path, "review")
    assert ack is not None
    assert ack["status"] == "done"


def test_process_once_idles_when_no_executable_action(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "action": "wait_for_review",
        "summary": "Stop coding and wait for review-work verdict.",
        "pending_commits": [],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "codex",
        "runner": "agent",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["agent"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "waiting for review",
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "codex")
    assert result["status"] == "idle"
    assert result["executed"] is False
    assert result["reason"] == "waiting_for_review"


def test_action_prompt_supports_supervisor_mailbox_actions() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    main_contract_mailbox = {"role_contract": "main-contract"}
    review_contract_mailbox = {"role_contract": "review-contract"}
    coding_contract_mailbox = {"role_contract": "coding-contract"}

    main_assign = executor_module._action_prompt("main", {"action": "assign_next_batch", **main_contract_mailbox})
    main_monitor = executor_module._action_prompt("main", {"action": "monitor", **main_contract_mailbox})
    main_rework = executor_module._action_prompt("main", {"action": "hold_merge_and_wait_for_rework", **main_contract_mailbox})
    review_idle = executor_module._action_prompt("review", {"action": "idle", **review_contract_mailbox})
    review_rework = executor_module._action_prompt("review", {"action": "wait_for_rework_submissions", **review_contract_mailbox})
    coding_wait = executor_module._action_prompt("codex", {"action": "wait_for_assignment", **coding_contract_mailbox})
    coding_rework = executor_module._action_prompt("codex", {"action": "consume_reject_cleanup_and_sync_main", **coding_contract_mailbox})

    assert main_assign is not None
    assert "下一批 assignment/分配动作" in main_assign
    assert main_monitor is not None
    assert "workflow objects" in main_monitor
    assert main_rework is not None
    assert "禁止 merge" in main_rework
    assert review_idle is not None
    assert "汇报 idle 并保持待命" in review_idle
    assert review_rework is not None
    assert "等待 coding 分支基于 REJECT 重新提交" in review_rework
    assert coding_wait is not None
    assert "等待分配并保持待命" in coding_wait
    assert coding_rework is not None
    assert "消费当前 REJECT" in coding_rework


def test_passive_resolution_supports_rework_wait_states() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    review_wait = executor_module._passive_action_resolution("review", {"action": "wait_for_rework_submissions", "dirty_files": []})
    main_wait = executor_module._passive_action_resolution("main", {"action": "hold_merge_and_wait_for_rework", "dirty_files": []})

    assert review_wait is not None
    assert review_wait["status"] == "idle"
    assert review_wait["reason"] == "waiting_for_rework_submissions"
    assert main_wait is not None
    assert main_wait["status"] == "blocked"
    assert main_wait["reason"] == "waiting_for_rework_before_merge"


def test_process_once_handles_missing_mailbox_gracefully(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    result = executor_module.process_once(tmp_path, "main")

    assert result["status"] == "idle"
    assert result["executed"] is False
    assert result["reason"] == "mailbox_missing"


def test_process_triage_creates_assignment_and_updates_finding(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    audit_state_module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)
    _write_assignments_md(tmp_path)

    assert (
        audit_state_module.main(
            [
                "--repo-root",
                str(tmp_path),
                "finding",
                "--agent",
                "audit-a",
                "--title",
                "Audit issue",
                "--summary",
                "Need codex assignment",
                "--severity",
                "p1",
                "--spec",
                "workflow-closed-loop",
                "--task-ref",
                "4.2",
                "--target-agent",
                "codex",
                "--target-branch",
                "codex-work",
                "--file",
                "owlclaw/agent/runtime/runtime.py",
                "--dimension",
                "core_logic",
                "--lens",
                "failure",
                "--evidence",
                "Confirmed from code path in runtime.py.",
                "--json",
            ]
        )
        == 0
    )
    finding_path = next((tmp_path / ".kiro" / "runtime" / "findings" / "open").glob("*.json"))
    finding_payload = json.loads(finding_path.read_text(encoding="utf-8"))

    objects_module = sys.modules["workflow_objects"]
    triage = objects_module.create_object(
        tmp_path,
        "triage_decision",
        payload={
            "status": "pending",
            "owner": "main",
            "finding_ids": [finding_payload["id"]],
            "decision": "pending",
            "reason": "await triage",
            "assigned_spec": "workflow-closed-loop",
            "target_worktree": "codex-work",
        },
    )

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "main",
        "action": "process_triage",
        "summary": "Process triage.",
        "pending_commits": [],
        "blockers": [],
        "dirty_files": [],
        "object_type": "triage_decision",
        "object_id": triage["id"],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "main",
        "runner": "codex",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["codex", "exec"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "triage complete",
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "main")
    assert result["status"] == "done"

    assignments = objects_module.list_objects(tmp_path, "assignment")
    assert len(assignments) == 1
    assert assignments[0]["target_agent"] == "codex"

    updated_triage = objects_module.read_object(tmp_path, "triage_decision", triage["id"])
    assert updated_triage["status"] == "accepted"

    updated_finding = objects_module.read_object(tmp_path, "finding", finding_payload["id"])
    assert updated_finding["status"] == "assigned"


def test_process_triage_blocks_when_assignment_is_outside_manual_boundary(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    audit_state_module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)
    _write_assignments_md(tmp_path, include_spec="different-spec")

    assert (
        audit_state_module.main(
            [
                "--repo-root",
                str(tmp_path),
                "finding",
                "--agent",
                "audit-a",
                "--title",
                "Audit issue",
                "--summary",
                "Need codex assignment",
                "--severity",
                "p1",
                "--spec",
                "workflow-closed-loop",
                "--task-ref",
                "4.4",
                "--target-agent",
                "codex",
                "--target-branch",
                "codex-work",
                "--file",
                "owlclaw/agent/runtime/runtime.py",
                "--dimension",
                "core_logic",
                "--lens",
                "drift",
                "--evidence",
                "Finding is outside assigned spec in tested matrix.",
            ]
        )
        == 0
    )
    finding_path = next((tmp_path / ".kiro" / "runtime" / "findings" / "open").glob("*.json"))
    finding_payload = json.loads(finding_path.read_text(encoding="utf-8"))
    objects_module = sys.modules["workflow_objects"]
    triage = objects_module.create_object(
        tmp_path,
        "triage_decision",
        payload={
            "status": "pending",
            "owner": "main",
            "finding_ids": [finding_payload["id"]],
            "decision": "pending",
            "reason": "await triage",
            "assigned_spec": "workflow-closed-loop",
            "target_worktree": "codex-work",
            "claim": None,
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "main",
                "action": "process_triage",
                "summary": "Process triage.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "triage_decision",
                "object_id": triage["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "main",
        "runner": "codex",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["codex", "exec"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "triage complete",
        "error_kind": "",
    }

    result = executor_module.process_once(tmp_path, "main")

    assert result["status"] == "blocked"
    blockers = objects_module.list_objects(tmp_path, "blocker")
    assert len(blockers) == 1
    assert "not assigned" in blockers[0]["summary"]
    assert objects_module.read_object(tmp_path, "triage_decision", triage["id"])["status"] == "deferred"


def test_execute_assignment_creates_delivery(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    assignment = objects_module.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "pending",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["5.2"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "codex",
                "branch": "codex-work",
                "action": "execute_assignment",
                "summary": "Execute assignment.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "assignment",
                "object_id": assignment["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "codex",
        "runner": "agent",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["agent"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "coding complete",
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "codex")
    assert result["status"] == "done"
    deliveries = objects_module.list_objects(tmp_path, "delivery")
    assert len(deliveries) == 1
    assert deliveries[0]["assignment_id"] == assignment["id"]
    updated_assignment = objects_module.read_object(tmp_path, "assignment", assignment["id"])
    assert updated_assignment["status"] == "delivered"
    assert updated_assignment["claim"] is None


def test_review_delivery_creates_verdict(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    delivery = objects_module.create_object(
        tmp_path,
        "delivery",
        payload={
            "status": "pending_review",
            "owner": "review",
            "assignment_id": "assignment-1",
            "branch": "codex-work",
            "commit_refs": [],
            "changed_files": [],
            "tests_run": [],
            "summary": "delivery ready",
            "blockers": [],
            "claim": None,
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "review",
                "action": "review_delivery",
                "summary": "Review delivery.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "delivery",
                "object_id": delivery["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "review",
        "runner": "claude",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["claude", "-p"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "review approve",
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "review")
    assert result["status"] == "done"
    verdicts = objects_module.list_objects(tmp_path, "review_verdict")
    assert len(verdicts) == 1
    assert verdicts[0]["delivery_id"] == delivery["id"]
    assert objects_module.read_object(tmp_path, "delivery", delivery["id"])["status"] == "approved"


def test_review_delivery_fix_needed_creates_new_findings_and_returns_assignment(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    assignment = objects_module.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "delivered",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["6.3"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    delivery = objects_module.create_object(
        tmp_path,
        "delivery",
        payload={
            "status": "pending_review",
            "owner": "review",
            "assignment_id": assignment["id"],
            "branch": "codex-work",
            "commit_refs": [],
            "changed_files": [],
            "tests_run": [],
            "summary": "delivery ready",
            "blockers": [],
            "claim": None,
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "review",
                "action": "review_delivery",
                "summary": "Review delivery.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "delivery",
                "object_id": delivery["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "review",
        "runner": "claude",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["claude", "-p"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": json.dumps(
            {
                "verdict": "FIX_NEEDED",
                "merge_ready": False,
                "notes": "Need follow-up",
                "new_findings": [
                    {
                        "title": "Review issue",
                        "summary": "Missing regression coverage",
                        "severity": "medium",
                        "spec": "workflow-closed-loop",
                        "task_ref": "6.3",
                        "target_agent": "codex",
                        "target_branch": "codex-work",
                    }
                ],
            }
        ),
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "review")
    assert result["status"] == "done"
    verdicts = objects_module.list_objects(tmp_path, "review_verdict")
    assert verdicts[0]["verdict"] == "FIX_NEEDED"
    assert verdicts[0]["new_finding_ids"]
    assert objects_module.read_object(tmp_path, "delivery", delivery["id"])["status"] == "fix_needed"
    assert objects_module.read_object(tmp_path, "assignment", assignment["id"])["status"] == "returned"


def test_apply_merge_decision_closes_chain(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    finding = objects_module.create_object(
        tmp_path,
        "finding",
        payload={
            "status": "assigned",
            "owner": "main",
            "title": "Audit finding",
            "summary": "Needs coding",
            "severity": "p1",
            "refs": {"spec": "workflow-closed-loop", "task_ref": "7.2"},
            "relations": {"parent_delivery_id": "", "parent_verdict_id": ""},
        },
    )
    assignment = objects_module.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "delivered",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["7.2"],
            "finding_ids": [finding["id"]],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    delivery = objects_module.create_object(
        tmp_path,
        "delivery",
        payload={
            "status": "approved",
            "owner": "review",
            "assignment_id": assignment["id"],
            "branch": "codex-work",
            "commit_refs": [],
            "changed_files": [],
            "tests_run": [],
            "summary": "delivery ready",
            "blockers": [],
            "claim": None,
        },
    )
    verdict = objects_module.create_object(
        tmp_path,
        "review_verdict",
        payload={
            "status": "applied",
            "owner": "main",
            "delivery_id": delivery["id"],
            "verdict": "APPROVE",
            "new_finding_ids": [],
            "merge_ready": True,
            "notes": "approved",
            "claim": None,
        },
    )
    merge = objects_module.create_object(
        tmp_path,
        "merge_decision",
        payload={
            "status": "pending",
            "owner": "main",
            "verdict_id": verdict["id"],
            "decision": "merge_review_work",
            "summary": "Merge.",
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "main",
                "action": "apply_merge_decision",
                "summary": "Apply merge decision.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "merge_decision",
                "object_id": merge["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "main",
        "runner": "codex",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["codex", "exec"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "merge applied",
        "error_kind": "",
    }

    result = executor_module.process_once(tmp_path, "main")

    assert result["status"] == "done"
    assert objects_module.read_object(tmp_path, "merge_decision", merge["id"])["status"] == "merged"
    assert objects_module.read_object(tmp_path, "finding", finding["id"])["status"] == "merged"


def test_review_delivery_recovery_does_not_duplicate_verdicts(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    assignment = objects_module.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "delivered",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["11.3"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    delivery = objects_module.create_object(
        tmp_path,
        "delivery",
        payload={
            "status": "pending_review",
            "owner": "review",
            "assignment_id": assignment["id"],
            "branch": "codex-work",
            "commit_refs": [],
            "changed_files": [],
            "tests_run": [],
            "summary": "delivery ready",
            "blockers": [],
            "claim": None,
        },
    )
    mailbox = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_delivery",
        "summary": "Review delivery.",
        "pending_commits": [],
        "blockers": [],
        "dirty_files": [],
        "object_type": "delivery",
        "object_id": delivery["id"],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(mailbox, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "review",
        "runner": "claude",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["claude", "-p"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "review approve",
        "error_kind": "",
    }

    first = executor_module.process_once(tmp_path, "review")
    assert first["status"] == "done"
    state_path = tmp_path / ".kiro" / "runtime" / "executor-state" / "review.json"
    state_path.unlink(missing_ok=True)
    mailbox["summary"] = "Review delivery again after restart."
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(mailbox, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    second = executor_module.process_once(tmp_path, "review")

    assert second["status"] == "done"
    assert len(objects_module.list_objects(tmp_path, "review_verdict")) == 1


def test_process_verdict_recovery_does_not_duplicate_merge_decisions(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    verdict = objects_module.create_object(
        tmp_path,
        "review_verdict",
        payload={
            "status": "pending_main",
            "owner": "main",
            "delivery_id": "delivery-1",
            "verdict": "APPROVE",
            "new_finding_ids": [],
            "merge_ready": True,
            "notes": "ok",
            "claim": None,
        },
    )
    mailbox = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "main",
        "action": "process_verdict",
        "summary": "Process verdict.",
        "pending_commits": [],
        "blockers": [],
        "dirty_files": [],
        "object_type": "review_verdict",
        "object_id": verdict["id"],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "main",
        "runner": "codex",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["codex", "exec"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "process verdict",
        "error_kind": "",
    }

    executor_module.process_once(tmp_path, "main")
    (tmp_path / ".kiro" / "runtime" / "executor-state" / "main.json").unlink(missing_ok=True)
    mailbox["summary"] = "Process verdict again after restart."
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    executor_module.process_once(tmp_path, "main")

    assert len(objects_module.list_objects(tmp_path, "merge_decision")) == 1


def test_execute_assignment_failure_creates_blocker(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    assignment = objects_module.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "pending",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "workflow-closed-loop",
            "task_refs": ["5.3"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json").write_text(
        json.dumps(
            {
                "mailbox_version": 1,
                "generated_at": "2026-03-06T00:00:00+00:00",
                "agent": "codex",
                "branch": "codex-work",
                "action": "execute_assignment",
                "summary": "Execute assignment.",
                "pending_commits": [],
                "blockers": [],
                "dirty_files": [],
                "object_type": "assignment",
                "object_id": assignment["id"],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "codex",
        "runner": "agent",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["agent"],
        "returncode": 1,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "coding failed",
        "error_kind": "runtime_error",
    }
    result = executor_module.process_once(tmp_path, "codex")
    assert result["status"] == "blocked"
    assert objects_module.read_object(tmp_path, "assignment", assignment["id"])["status"] == "blocked"
    blockers = objects_module.list_objects(tmp_path, "blocker")
    assert len(blockers) == 1
    assert blockers[0]["source_id"] == assignment["id"]


def test_process_once_skips_already_processed_mailbox(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    fingerprint = executor_module._mailbox_fingerprint(mailbox_payload)
    state_path = tmp_path / ".kiro" / "runtime" / "executor-state" / "review.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "agent": "review",
                "updated_at": "2026-03-06T00:00:01+00:00",
                "fingerprint": fingerprint,
                "status": "done",
                "action": "review_pending_commits",
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = executor_module.process_once(tmp_path, "review")
    assert result["executed"] is False
    assert result["reason"] == "already_processed"


def test_invoke_runner_uses_wrapper_when_direct_command_missing(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    original_which = executor_module.shutil.which
    original_run = executor_module.subprocess.run

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    calls: list[list[str]] = []

    def fake_which(name: str):
        mapping = {
            "codex": None,
            "codex.ps1": "C:\\Users\\yeemi\\AppData\\Roaming\\npm\\codex.ps1",
            "pwsh": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        }
        return mapping.get(name)

    def fake_run(command, **kwargs):
        calls.append(command)
        last_message_path = Path(command[-2])
        last_message_path.write_text("ok", encoding="utf-8")
        return Result()

    executor_module.shutil.which = fake_which
    executor_module.subprocess.run = fake_run
    try:
        result = executor_module._invoke_runner(tmp_path, "main", workdir=tmp_path, prompt="hello")
    finally:
        executor_module.shutil.which = original_which
        executor_module.subprocess.run = original_run

    assert calls
    assert calls[0][:3] == ["C:\\Program Files\\PowerShell\\7\\pwsh.exe", "-File", "C:\\Users\\yeemi\\AppData\\Roaming\\npm\\codex.ps1"]
    assert result["returncode"] == 0


def test_invoke_runner_supports_agent_backend(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    original_which = executor_module.shutil.which
    original_run = executor_module.subprocess.run

    class Result:
        returncode = 0
        stdout = json.dumps({"type": "result", "result": "agent completed"})
        stderr = ""

    calls: list[list[str]] = []

    def fake_which(name: str):
        mapping = {
            "agent": None,
            "agent.ps1": "C:\\Users\\yeemi\\AppData\\Local\\cursor-agent\\agent.ps1",
            "pwsh": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        }
        return mapping.get(name)

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    executor_module.shutil.which = fake_which
    executor_module.subprocess.run = fake_run
    try:
        result = executor_module._invoke_runner(tmp_path, "codex", workdir=tmp_path, prompt="hello")
    finally:
        executor_module.shutil.which = original_which
        executor_module.subprocess.run = original_run

    assert calls
    assert calls[0][:3] == ["C:\\Program Files\\PowerShell\\7\\pwsh.exe", "-File", "C:\\Users\\yeemi\\AppData\\Local\\cursor-agent\\agent.ps1"]
    assert result["runner"] == "agent"
    assert result["last_message"] == "agent completed"


def test_mailbox_fingerprint_ignores_generated_at() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    first = {
        "generated_at": "2026-03-06T00:00:00+00:00",
        "action": "review_pending_commits",
        "stage": "review",
        "summary": "x",
        "pending_commits": ["a"],
        "blockers": [],
        "dirty_files": [],
    }
    second = {**first, "generated_at": "2026-03-06T00:01:00+00:00"}
    assert executor_module._mailbox_fingerprint(first) == executor_module._mailbox_fingerprint(second)


def test_detect_invalid_output_flags_ready_reply() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    assert executor_module._detect_invalid_output("What would you like me to work on next?") == "non_executing_reply"


def test_process_once_marks_timeout_blocked(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def fake_invoke(*args, **kwargs):
        raise executor_module.subprocess.TimeoutExpired(cmd=["claude"], timeout=120)

    executor_module._invoke_runner = fake_invoke
    result = executor_module.process_once(tmp_path, "review")
    assert result["status"] == "blocked"
    assert result["result"]["error_kind"] == "timeout"


def test_timeout_for_action_extends_review_and_triage_windows() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    assert (
        executor_module._timeout_for_action("review", {"action": "review_pending_commits"})
        == executor_module.LONG_RUNNING_TIMEOUT_SECONDS
    )
    assert (
        executor_module._timeout_for_action("main", {"action": "process_triage"})
        == executor_module.TRIAGE_TIMEOUT_SECONDS
    )
    assert (
        executor_module._timeout_for_action("codex", {"action": "execute_assignment"})
        == executor_module.RUNNER_TIMEOUT_SECONDS
    )
