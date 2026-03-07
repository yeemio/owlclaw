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


def _write_assignments_md(repo_root: Path) -> None:
    path = repo_root / ".kiro" / "WORKTREE_ASSIGNMENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Worktree 任务分配

### owlclaw-codex（编码 1）

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-codex\\` |
| 分支 | `codex-work` |
| 工作状态 | `WORKING` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **workflow-closed-loop** | ✅ 1/1 | `scripts/` |

### codex-work 分配（当前批次）

| Spec | Phase | Task | Finding | 优先级 | 状态 |
|------|-------|------|---------|--------|------|
| **workflow-closed-loop** | Phase 16 | #47 | Runtime | Low | 🟡 进行中 |

### owlclaw-codex-gpt（编码 2）

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-codex-gpt\\` |
| 分支 | `codex-gpt-work` |
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


def test_full_closed_loop_from_audit_to_merge(tmp_path: Path) -> None:
    status_module = _load_module("workflow_status", "scripts/workflow_status.py")
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects_module = _load_module("workflow_objects", "scripts/workflow_objects.py")
    orchestrator_module = _load_module("workflow_orchestrator", "scripts/workflow_orchestrator.py")
    audit_state_module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

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
                "Need coding fix",
                "--severity",
                "p1",
                "--spec",
                "workflow-closed-loop",
                "--task-ref",
                "11.2",
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
                "Traced bad path in runtime.py.",
            ]
        )
        == 0
    )

    snapshot = status_module.WorkflowSnapshot(
        repo_root=str(tmp_path),
        audit=status_module.AuditSummary(1, 1, 0, "0/1", "进行中", "workflow-closed-loop"),
        worktrees=[
            status_module.WorktreeState("main", "main", str(tmp_path), "orchestrator", True, [], 0, 0, []),
            status_module.WorktreeState("review", "review-work", str(tmp_path / "review"), "review", True, [], 0, 0, []),
            status_module.WorktreeState("codex", "codex-work", str(tmp_path / "codex"), "coding", True, [], 0, 0, []),
            status_module.WorktreeState("codex-gpt", "codex-gpt-work", str(tmp_path / "codex-gpt"), "coding", True, [], 0, 0, []),
        ],
        next_action="stable",
        blockers=[],
    )

    executor_module._invoke_runner = lambda repo_root, agent, **kwargs: {
        "agent": agent,
        "runner": "codex" if agent == "main" else ("claude" if agent == "review" else "agent"),
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": [agent],
        "returncode": 0,
        "last_message_path": str(tmp_path / f"{agent}.txt"),
        "log_path": str(tmp_path / f"{agent}.log"),
        "last_message": (
            json.dumps({"verdict": "APPROVE", "merge_ready": True, "notes": "ok", "new_findings": []})
            if agent == "review"
            else f"{agent} complete"
        ),
        "error_kind": "",
    }

    orchestrator_module.write_runtime_files(tmp_path, snapshot)
    main_result = executor_module.process_once(tmp_path, "main")
    assert main_result["status"] == "done"

    orchestrator_module.write_runtime_files(tmp_path, snapshot)
    coding_result = executor_module.process_once(tmp_path, "codex")
    assert coding_result["status"] == "done"

    orchestrator_module.write_runtime_files(tmp_path, snapshot)
    review_result = executor_module.process_once(tmp_path, "review")
    assert review_result["status"] == "done"

    orchestrator_module.write_runtime_files(tmp_path, snapshot)
    verdict_result = executor_module.process_once(tmp_path, "main")
    assert verdict_result["status"] == "done"

    orchestrator_module.write_runtime_files(tmp_path, snapshot)
    merge_result = executor_module.process_once(tmp_path, "main")
    assert merge_result["status"] == "done"

    findings = objects_module.list_objects(tmp_path, "finding")
    assignments = objects_module.list_objects(tmp_path, "assignment")
    deliveries = objects_module.list_objects(tmp_path, "delivery")
    verdicts = objects_module.list_objects(tmp_path, "review_verdict")
    merges = objects_module.list_objects(tmp_path, "merge_decision")

    assert len(findings) == 1
    assert findings[0]["status"] == "merged"
    assert len(assignments) == 1
    assert assignments[0]["status"] == "delivered"
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "approved"
    assert len(verdicts) == 1
    assert verdicts[0]["status"] == "applied"
    assert len(merges) == 1
    assert merges[0]["status"] == "merged"
