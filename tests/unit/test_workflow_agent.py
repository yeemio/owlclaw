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


def test_process_once_writes_dispatch_heartbeat_and_seen_ack(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    agent_module = _load_module("workflow_agent", "scripts/workflow_agent.py")

    runtime_dir = tmp_path / ".kiro" / "runtime" / "mailboxes"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "stage": "review",
        "owner": "review",
        "action": "review_pending_commits",
        "priority": "high",
        "summary": "Review pending coding submissions in order: codex-work.",
        "blockers": [],
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
    }
    (runtime_dir / "review.json").write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    result = agent_module.process_once(tmp_path, "review")
    assert result["changed"] is True
    assert result["ack"]["status"] == "seen"

    dispatch_path = tmp_path / ".kiro" / "runtime" / "dispatch" / "review.md"
    heartbeat_path = tmp_path / ".kiro" / "runtime" / "heartbeats" / "review.json"
    state_path = tmp_path / ".kiro" / "runtime" / "agent-state" / "review.json"
    assert dispatch_path.exists()
    assert heartbeat_path.exists()
    assert state_path.exists()

    dispatch_text = dispatch_path.read_text(encoding="utf-8")
    assert "审校当前 mailbox 指定的 coding branch 代码提交" in dispatch_text
    assert "workflow_mailbox.py ack --agent review --status started" in dispatch_text

    heartbeat_payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    assert heartbeat_payload["mailbox_changed"] is True
    assert heartbeat_payload["ack_status"] == "seen"


def test_main_once_quiet_when_mailbox_unchanged(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    agent_module = _load_module("workflow_agent", "scripts/workflow_agent.py")

    runtime_dir = tmp_path / ".kiro" / "runtime" / "mailboxes"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "stage": "review",
        "owner": "review",
        "action": "wait_for_review",
        "priority": "high",
        "summary": "Stop coding and wait for review-work verdict.",
        "blockers": ["codex-work is waiting for review-work review"],
        "pending_commits": ["abc fix"],
    }
    (runtime_dir / "codex.json").write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    assert agent_module.main(["--repo-root", str(tmp_path), "--agent", "codex", "--once"]) == 0
    first_output = capsys.readouterr().out
    assert "mailbox changed: yes" in first_output

    assert agent_module.main(["--repo-root", str(tmp_path), "--agent", "codex", "--once"]) == 0
    second_output = capsys.readouterr().out
    assert second_output == ""
