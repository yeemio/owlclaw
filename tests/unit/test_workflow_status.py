from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/workflow_status.py")
    spec = importlib.util.spec_from_file_location("workflow_status", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_audit_report_extracts_totals(tmp_path: Path) -> None:
    module = _load_module()
    report = tmp_path / "DEEP_AUDIT_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "## Executive Summary",
                "",
                "**Total Findings**: 44 (P0: 0, P1: 2, Low: 42)",
                "- P1/Medium: 2",
                "- Low: 42",
            ]
        ),
        encoding="utf-8",
    )

    summary = module._parse_audit_report(report)

    assert summary.total_findings == 44
    assert summary.p1 == 2
    assert summary.low == 42


def test_merge_audit_progress_extracts_spec_row(tmp_path: Path) -> None:
    module = _load_module()
    scan = tmp_path / "SPEC_TASKS_SCAN.md"
    scan.write_text(
        "\n".join(
            [
                "| Spec 名称 | 路径 | 状态 | 覆盖模块 |",
                "|-----------|------|------|---------|",
                "| **audit-deep-remediation** | `.kiro/specs/audit-deep-remediation/` | 🟡 三层齐全，进行中（20/29） | 深度审计修复：待 review-work 审校 |",
            ]
        ),
        encoding="utf-8",
    )

    summary = module._merge_audit_progress(
        module.AuditSummary(total_findings=44, p1=2, low=42, spec_progress=None, spec_status=None, spec_summary=None),
        scan,
    )

    assert summary.spec_progress == "20/29"
    assert summary.spec_status is not None
    assert "进行中" in summary.spec_status
    assert summary.spec_summary == "深度审计修复：待 review-work 审校"


def test_decide_next_action_prefers_review_over_clean_message() -> None:
    module = _load_module()
    worktrees = [
        module.WorktreeState("main", "main", "D:/repo", "orchestrator", True, [], 0, 0, []),
        module.WorktreeState("review", "review-work", "D:/repo-review", "review", True, [], 0, 0, []),
        module.WorktreeState("codex", "codex-work", "D:/repo-codex", "coding", True, [], 2, 0, ["abc fix"]),
        module.WorktreeState("codex-gpt", "codex-gpt-work", "D:/repo-codex-gpt", "coding", True, [], 0, 0, []),
    ]

    next_action, blockers = module._decide_next_action(worktrees)

    assert next_action == "review-work should review pending coding branches: codex-work"
    assert blockers == []


def test_decide_next_action_reports_dirty_main_blocker() -> None:
    module = _load_module()
    worktrees = [
        module.WorktreeState("main", "main", "D:/repo", "orchestrator", False, ["M file"], 0, 0, []),
        module.WorktreeState("review", "review-work", "D:/repo-review", "review", True, [], 0, 0, []),
        module.WorktreeState("codex", "codex-work", "D:/repo-codex", "coding", True, [], 0, 0, []),
        module.WorktreeState("codex-gpt", "codex-gpt-work", "D:/repo-codex-gpt", "coding", True, [], 0, 0, []),
    ]

    next_action, blockers = module._decide_next_action(worktrees)

    assert next_action == "clean dirty worktrees before next orchestration step"
    assert blockers == ["main worktree has uncommitted changes"]
