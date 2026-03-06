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


def test_write_ack_and_read_mailbox(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

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
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    ack = mailbox_module.write_ack(
        tmp_path,
        "codex",
        status="started",
        note="picked up review queue",
        task_ref="D23",
        commit_ref="abc1234",
    )
    assert ack["status"] == "started"

    read_mailbox = mailbox_module.read_mailbox(tmp_path, "codex")
    assert read_mailbox["action"] == "wait_for_review"

    read_ack = mailbox_module.read_ack(tmp_path, "codex")
    assert read_ack is not None
    assert read_ack["task_ref"] == "D23"
    assert read_ack["commit_ref"] == "abc1234"


def test_main_pull_and_ack_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

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
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    assert mailbox_module.main(
        ["--repo-root", str(tmp_path), "ack", "--agent", "review", "--status", "seen", "--json"]
    ) == 0
    ack_output = json.loads(capsys.readouterr().out)
    assert ack_output["agent"] == "review"
    assert ack_output["status"] == "seen"

    assert mailbox_module.main(["--repo-root", str(tmp_path), "pull", "--agent", "review", "--json"]) == 0
    pull_output = json.loads(capsys.readouterr().out)
    assert pull_output["mailbox"]["action"] == "review_pending_commits"
    assert pull_output["ack"]["status"] == "seen"
