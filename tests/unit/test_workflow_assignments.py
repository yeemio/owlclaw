from __future__ import annotations

import importlib.util
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


def test_validate_assignment_target_reads_manual_matrix(tmp_path: Path) -> None:
    module = _load_module("workflow_assignments", "scripts/workflow_assignments.py")
    path = tmp_path / ".kiro" / "WORKTREE_ASSIGNMENTS.md"
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

    ok, reason = module.validate_assignment_target(
        tmp_path,
        target_agent="codex",
        target_branch="codex-work",
        spec_name="workflow-closed-loop",
    )
    assert ok is True
    assert reason == ""

    ok, reason = module.validate_assignment_target(
        tmp_path,
        target_agent="codex",
        target_branch="codex-work",
        spec_name="wrong-spec",
    )
    assert ok is False
    assert "not assigned" in reason


def test_validate_assignment_target_tolerates_heading_variants(tmp_path: Path) -> None:
    module = _load_module("workflow_assignments_heading_variants", "scripts/workflow_assignments.py")
    path = tmp_path / ".kiro" / "WORKTREE_ASSIGNMENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Worktree 任务分配

### owlclaw-review - 技术经理

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-review\\` |
| 分支 | `review-work` |
| 工作状态 | `DONE` |

### owlclaw-codex - 编码一（当前批次）

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

### owlclaw-codex-gpt - 编码二 / 候补

| 字段 | 值 |
|------|---|
| 目录 | `D:\\AI\\owlclaw-codex-gpt\\` |
| 分支 | `codex-gpt-work` |
| 工作状态 | `DONE` |

**当前分配的 spec**：

| Spec | 进度 | 涉及路径 |
|------|------|---------|
| **other-spec** | ✅ 1/1 | `scripts/` |
""",
        encoding="utf-8",
    )

    ok, reason = module.validate_assignment_target(
        tmp_path,
        target_agent="codex",
        target_branch="codex-work",
        spec_name="workflow-closed-loop",
    )
    assert ok is True
    assert reason == ""
