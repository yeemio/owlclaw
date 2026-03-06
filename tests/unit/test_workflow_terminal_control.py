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
    assert control._message_for_audit("audit-a") == "继续深度审计"
    assert control._message_for_audit("audit-b") == "继续审计统筹"
    assert control.TITLE_MAP["review"] == ["owlclaw-review", "claude"]


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

    heartbeat_dir = tmp_path / ".kiro" / "runtime" / "heartbeats"
    ack_dir = tmp_path / ".kiro" / "runtime" / "acks"
    heartbeat_dir.mkdir(parents=True, exist_ok=True)
    ack_dir.mkdir(parents=True, exist_ok=True)
    heartbeat_dir.joinpath("review.json").write_text(
        json.dumps({"polled_at": "2026-03-06T00:00:30+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    ack_dir.joinpath("review.json").write_text(
        json.dumps({"acked_at": "2026-03-06T00:00:30+00:00", "status": "seen"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    control._seconds_since = lambda value: 10.0
    result = control.drive_once(tmp_path, "review")
    assert result["delivered"] is False
    assert result["reason"] == "fresh_runtime"


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


def test_drive_once_resends_when_heartbeat_stale(tmp_path: Path) -> None:
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
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    fingerprint = control._fingerprint(mailbox_payload, "继续审校")
    (tmp_path / ".kiro" / "runtime" / "terminal-control").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kiro" / "runtime" / "terminal-control" / "review.json").write_text(
        json.dumps({"agent": "review", "fingerprint": fingerprint, "sent_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (tmp_path / ".kiro" / "runtime" / "heartbeats").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kiro" / "runtime" / "acks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kiro" / "runtime" / "heartbeats" / "review.json").write_text(
        json.dumps({"polled_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (tmp_path / ".kiro" / "runtime" / "acks" / "review.json").write_text(
        json.dumps({"acked_at": "2026-03-06T00:00:00+00:00", "status": "seen"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    class Result:
        returncode = 0
        stdout = "sent"
        stderr = ""

    control._seconds_since = lambda value: 999.0
    control._send_to_window_candidates = lambda repo_root, window_titles, message, **kwargs: (window_titles[0], Result())
    result = control.drive_once(tmp_path, "review", stale_seconds=180)
    assert result["delivered"] is True
    assert result["decision_reason"] == "stale_heartbeat"


def test_drive_all_includes_audit_terminals(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    for agent in mailbox_module.VALID_AGENT_NAMES:
        mailbox_payload = {
            "mailbox_version": 1,
            "generated_at": "2026-03-06T00:00:00+00:00",
            "agent": agent,
            "action": "wait_for_assignment",
            "stage": "stable",
            "summary": "Waiting for the next action.",
            "pending_commits": [],
            "dirty_files": [],
        }
        mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / f"{agent}.json"
        mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    class Result:
        returncode = 0
        stdout = "sent"
        stderr = ""

    control._send_to_window = lambda repo_root, window_title, message: Result()
    results = control.drive_all(tmp_path, force=True)
    agents = {result["agent"] for result in results}
    assert agents == set(control.ALL_TERMINAL_TARGETS)


def test_pause_flag_round_trip(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")

    assert control.is_paused(tmp_path) is False
    control.set_paused(tmp_path, True)
    assert control.is_paused(tmp_path) is True
    control.set_paused(tmp_path, False)
    assert control.is_paused(tmp_path) is False


def test_window_manifest_process_id_lookup(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    runtime_dir = tmp_path / ".kiro" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": "2026-03-06T00:00:00+00:00",
        "windows": {
            "main": {"pid": 1234, "hwnd": 4321, "title": "owlclaw-main"},
            "review": {"pid": 5678, "hwnd": 8765, "title": "owlclaw-review"},
        },
    }
    (runtime_dir / "terminal-windows.json").write_text(json.dumps(manifest, ensure_ascii=True), encoding="utf-8")

    assert control._window_process_id(tmp_path, "main") == 1234
    assert control._window_process_id(tmp_path, "review") == 5678
    assert control._window_process_id(tmp_path, "codex") is None
    assert control._window_handle(tmp_path, "main") == 4321
    assert control._window_handle(tmp_path, "review") == 8765
    assert control._window_handle(tmp_path, "codex") is None
