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


def test_message_mapping_uses_fixed_utterances() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")

    assert control._message_for_mailbox("main", {"action": "clean_local_changes"}) == "统筹"
    assert control._message_for_mailbox("review", {"action": "review_pending_commits"}) == "继续审校"
    assert control._message_for_mailbox("codex", {"action": "wait_for_review"}) == "继续spec循环"


def test_drive_once_skips_same_fingerprint(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "stage": "review",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["abc"],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    fingerprint = control._fingerprint(mailbox_payload, "继续审校")
    state_path = tmp_path / ".kiro" / "runtime" / "terminal-control" / "review.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"agent": "review", "fingerprint": fingerprint}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    result = control.drive_once(tmp_path, "review")
    assert result["delivered"] is False
    assert result["reason"] == "already_sent"


def test_drive_once_records_delivery(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "action": "wait_for_review",
        "stage": "review",
        "summary": "Stop coding and wait for review-work verdict.",
        "pending_commits": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    class Result:
        returncode = 0
        stdout = "sent:owlclaw-codex:继续spec循环"
        stderr = ""

    control._send_to_window = lambda repo_root, window_title, message: Result()
    result = control.drive_once(tmp_path, "codex")
    assert result["delivered"] is True
    assert result["message"] == "继续spec循环"
