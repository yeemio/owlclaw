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

    assert "统筹与主线收口" in control._message_for_mailbox("main", {"action": "clean_local_changes"})
    assert "统筹" in control._message_for_mailbox("main", {"action": "assign_next_batch"})
    assert "统筹" in control._message_for_mailbox("main", {"action": "monitor"})
    assert "assignment" in control._message_for_mailbox("main", {"action": "process_triage"})
    assert "统筹" in control._message_for_mailbox("main", {"action": "hold_merge_and_wait_for_rework"})
    assert "代码审校门" in control._message_for_mailbox("review", {"action": "review_pending_commits"})
    assert "继续审校" in control._message_for_mailbox("review", {"action": "wait_for_rework_submissions"})
    assert "继续审校" in control._message_for_mailbox("review", {"action": "idle"})
    assert "编码执行" in control._message_for_mailbox("codex", {"action": "cleanup_or_commit_local_changes"})
    assert "继续spec循环" in control._message_for_mailbox("codex", {"action": "wait_for_review"})
    assert "继续spec循环" in control._message_for_mailbox("codex", {"action": "wait_for_assignment"})
    assert "继续spec循环" in control._message_for_mailbox("codex", {"action": "consume_reject_cleanup_and_sync_main"})
    assert "deep-codebase-audit skill" in control._message_for_audit("audit-a")
    assert "不得修改代码" in control._message_for_audit("audit-a")
    assert "继续审计复核" in control._message_for_audit("audit-b")
    assert control.TITLE_MAP["review"] == ["owlclaw-review", "claude"]
    assert "audit-a" in control.ALL_TERMINAL_TARGETS
    assert "audit-b" in control.ALL_TERMINAL_TARGETS


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

    prompt = control._message_for_mailbox("review", mailbox_payload)
    assert prompt is not None
    fingerprint = control._fingerprint(mailbox_payload, prompt)
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
    assert result["reason"] == "agent_waiting_for_state_change"


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
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    prompt = control._message_for_mailbox("review", mailbox_payload)
    assert prompt is not None
    fingerprint = control._fingerprint(mailbox_payload, prompt)
    state_path = tmp_path / ".kiro" / "runtime" / "terminal-control" / "review.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "agent": "review",
                "fingerprint": fingerprint,
                "sent_at": "2026-03-06T00:00:00+00:00",
                "delivered": True,
            },
            ensure_ascii=True,
            indent=2,
        ),
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

    class Result:
        returncode = 0
        stdout = "sent"
        stderr = ""

    control._seconds_since = lambda value: 999.0
    control._send_to_window_candidates = lambda repo_root, window_titles, message, **kwargs: (window_titles[0], Result())
    result = control.drive_once(tmp_path, "review", retry_seconds=0, stale_seconds=180)
    assert result["delivered"] is True
    assert result["decision_reason"] == "stale_heartbeat"


def test_drive_once_skips_recent_executor_usage_limit_cooldown(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "main",
        "action": "process_triage",
        "stage": "assign",
        "summary": "Process triage.",
        "pending_commits": [],
        "dirty_files": [],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    prompt = control._message_for_mailbox("main", mailbox_payload)
    assert prompt is not None
    fingerprint = control._fingerprint(mailbox_payload, prompt)
    state_path = tmp_path / ".kiro" / "runtime" / "terminal-control" / "main.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "agent": "main",
                "fingerprint": fingerprint,
                "sent_at": "2026-03-06T00:00:00+00:00",
                "delivered": True,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    heartbeat_dir = tmp_path / ".kiro" / "runtime" / "heartbeats"
    ack_dir = tmp_path / ".kiro" / "runtime" / "acks"
    executor_state_dir = tmp_path / ".kiro" / "runtime" / "executor-state"
    execution_dir = tmp_path / ".kiro" / "runtime" / "executions" / "main"
    heartbeat_dir.mkdir(parents=True, exist_ok=True)
    ack_dir.mkdir(parents=True, exist_ok=True)
    executor_state_dir.mkdir(parents=True, exist_ok=True)
    execution_dir.mkdir(parents=True, exist_ok=True)
    heartbeat_dir.joinpath("main.json").write_text(
        json.dumps({"polled_at": "2026-03-06T00:00:30+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    ack_dir.joinpath("main.json").write_text(
        json.dumps({"acked_at": "2026-03-06T00:00:30+00:00", "status": "seen"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    executor_state_dir.joinpath("main.json").write_text(
        json.dumps(
            {
                "agent": "main",
                "updated_at": "2026-03-06T00:01:00+00:00",
                "status": "blocked",
                "action": "process_triage",
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    execution_dir.joinpath("result.json").write_text(
        json.dumps({"error_kind": "usage_limit"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    def fake_seconds_since(value):
        text = str(value)
        if text.endswith("00:00:00+00:00"):
            return 999.0
        if text.endswith("00:00:30+00:00"):
            return 10.0
        if text.endswith("00:01:00+00:00"):
            return 60.0
        return 10.0

    control._seconds_since = fake_seconds_since
    result = control.drive_once(tmp_path, "main", retry_seconds=0, stale_seconds=180)
    assert result["delivered"] is False
    assert result["reason"] == "executor_cooldown_usage_limit"


def test_drive_once_records_delivery(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "action": "cleanup_or_commit_local_changes",
        "stage": "cleanup",
        "summary": "Clean or commit local changes before continuing.",
        "pending_commits": [],
        "dirty_files": ["M file.py"],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    class Result:
        returncode = 0
        stdout = "sent:owlclaw-codex:继续spec循环"
        stderr = ""

    control._send_to_window_candidates = lambda repo_root, window_titles, message, **kwargs: (window_titles[0], Result())
    result = control.drive_once(tmp_path, "codex", transport="sendkeys")
    assert result["delivered"] is True
    assert result["injected"] is True
    assert "继续spec循环" in result["message"]


def test_drive_once_resends_when_delivery_failed(tmp_path: Path) -> None:
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
    prompt = control._message_for_mailbox("review", mailbox_payload)
    assert prompt is not None
    fingerprint = control._fingerprint(mailbox_payload, prompt)
    (tmp_path / ".kiro" / "runtime" / "terminal-control").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kiro" / "runtime" / "terminal-control" / "review.json").write_text(
        json.dumps({"agent": "review", "fingerprint": fingerprint, "sent_at": "2026-03-06T00:00:00+00:00", "delivered": False}, ensure_ascii=True, indent=2),
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

    class Result:
        returncode = 0
        stdout = "sent"
        stderr = ""

    control._seconds_since = lambda value: 999.0 if str(value).endswith("00:00:00+00:00") else 10.0
    control._send_to_window_candidates = lambda repo_root, window_titles, message, **kwargs: (window_titles[0], Result())
    result = control.drive_once(tmp_path, "review", transport="sendkeys", retry_seconds=0)
    assert result["delivered"] is True
    assert result["decision_reason"] == "retry_after_failed_delivery"


def test_main_monitor_state_records_observe_only_prompt_by_default(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "main",
        "action": "monitor",
        "stage": "review",
        "summary": "No immediate main-branch action.",
        "pending_commits": [],
        "dirty_files": [],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    result = control.drive_once(tmp_path, "main")
    assert result["delivered"] is True
    assert result["injected"] is False
    observe_payload = json.loads((tmp_path / ".kiro" / "runtime" / "terminal-observe" / "main.json").read_text(encoding="utf-8"))
    assert observe_payload["transport"] == "disabled"
    assert "统筹" in result["message"]


def test_main_prompt_waits_for_state_change_after_first_send(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "main",
        "action": "assign_next_batch",
        "stage": "assign",
        "summary": "Coding and review queues are clear; assign the next batch before nudging agents.",
        "pending_commits": [],
        "dirty_files": [],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "main.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    prompt = control._message_for_mailbox("main", mailbox_payload)
    assert prompt is not None
    fingerprint = control._fingerprint(mailbox_payload, prompt)
    (tmp_path / ".kiro" / "runtime" / "terminal-control").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kiro" / "runtime" / "terminal-control" / "main.json").write_text(
        json.dumps({"agent": "main", "fingerprint": fingerprint, "sent_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    heartbeat_dir = tmp_path / ".kiro" / "runtime" / "heartbeats"
    ack_dir = tmp_path / ".kiro" / "runtime" / "acks"
    heartbeat_dir.mkdir(parents=True, exist_ok=True)
    ack_dir.mkdir(parents=True, exist_ok=True)
    heartbeat_dir.joinpath("main.json").write_text(
        json.dumps({"polled_at": "2026-03-06T00:00:30+00:00"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    ack_dir.joinpath("main.json").write_text(
        json.dumps({"acked_at": "2026-03-06T00:00:30+00:00", "status": "seen"}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    control._seconds_since = lambda value: 999.0 if str(value).endswith("00:00:00+00:00") else 10.0
    result = control.drive_once(tmp_path, "main", retry_seconds=0)
    assert result["delivered"] is False
    assert result["reason"] == "main_waiting_for_state_change"


def test_review_idle_state_records_observe_only_prompt_by_default(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "idle",
        "stage": "stable",
        "summary": "No coding branch is waiting for review.",
        "pending_commits": [],
        "dirty_files": [],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    result = control.drive_once(tmp_path, "review")
    assert result["delivered"] is True
    assert result["injected"] is False
    assert "继续审校" in result["message"]


def test_codex_wait_for_review_state_records_observe_only_prompt_by_default(tmp_path: Path) -> None:
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
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    result = control.drive_once(tmp_path, "codex")
    assert result["delivered"] is True
    assert result["injected"] is False
    assert "继续spec循环" in result["message"]


def test_codex_reject_rework_state_records_observe_only_prompt_by_default(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "action": "consume_reject_cleanup_and_sync_main",
        "stage": "assign",
        "summary": "Consume reject and rework.",
        "pending_commits": [],
        "dirty_files": ["M .kiro/specs/SPEC_TASKS_SCAN.md"],
    }
    (tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json").write_text(
        json.dumps(mailbox_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    result = control.drive_once(tmp_path, "codex")
    assert result["delivered"] is True
    assert result["injected"] is False
    assert "继续spec循环" in result["message"]


def test_audit_agent_without_state_is_not_auto_nudged(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")

    result = control.drive_once(tmp_path, "audit-a")
    assert result["delivered"] is False
    assert result["reason"] == "missing_audit_state"


def test_audit_agent_with_fresh_idle_state_is_nudged(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    audit_dir = tmp_path / ".kiro" / "runtime" / "audit-state"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.joinpath("audit-a.json").write_text(
        json.dumps({"agent": "audit-a", "status": "idle", "updated_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True),
        encoding="utf-8",
    )

    control._seconds_since = lambda value: 10.0
    result = control.drive_once(tmp_path, "audit-a")
    assert result["delivered"] is True
    assert result["injected"] is False
    assert result["decision_reason"] == "first_send"


def test_audit_agent_skips_recent_retry_for_same_idle_state(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    runtime_dir = tmp_path / ".kiro" / "runtime"
    (runtime_dir / "audit-state").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "terminal-control").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "audit-state" / "audit-a.json").write_text(
        json.dumps({"agent": "audit-a", "status": "idle", "updated_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True),
        encoding="utf-8",
    )
    fingerprint = json.dumps(
        {
            "action": "fixed",
            "dirty_files": [],
            "message": control._message_for_audit("audit-a"),
            "object_id": None,
            "object_type": None,
            "pending_commits": [],
            "stage": "fixed",
            "summary": "fixed audit prompt",
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    (runtime_dir / "terminal-control" / "audit-a.json").write_text(
        json.dumps({"agent": "audit-a", "fingerprint": fingerprint, "sent_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True),
        encoding="utf-8",
    )

    control._seconds_since = lambda value: 10.0
    result = control.drive_once(tmp_path, "audit-a", retry_seconds=120)
    assert result["delivered"] is False
    assert result["reason"] == "recent_attempt"


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

    results = control.drive_all(tmp_path, force=True)
    agents = {result["agent"] for result in results}
    assert agents == set(control.ALL_TERMINAL_TARGETS)


def test_workflow_config_matches_expected_topology() -> None:
    payload = json.loads(Path(".kiro/workflow_terminal_config.json").read_text(encoding="utf-8"))
    roles = {role["agent"]: role for role in payload["roles"]}

    assert roles["main"]["repo_path"] == "D:\\AI\\owlclaw"
    assert roles["main"]["controller"] == "codex"
    assert roles["audit-a"]["repo_path"] == "D:\\AI\\owlclaw"
    assert roles["audit-a"]["controller"] == "agent"
    assert roles["audit-b"]["repo_path"] == "D:\\AI\\owlclaw"
    assert "deep-codebase-audit skill" in roles["audit-a"]["default_prompt"]
    assert "不得修改代码" in roles["audit-b"]["default_prompt"]
    assert roles["review"]["repo_path"] == "D:\\AI\\owlclaw-review"
    assert roles["review"]["controller"] == "claude"
    assert roles["codex"]["repo_path"] == "D:\\AI\\owlclaw-codex"
    assert roles["codex"]["controller"] == "agent"
    assert roles["codex-gpt"]["repo_path"] == "D:\\AI\\owlclaw-codex-gpt"
    assert roles["codex-gpt"]["controller"] == "agent"


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


def test_launch_state_process_id_takes_priority_over_manifest(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    runtime_dir = tmp_path / ".kiro" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "launch-state").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "terminal-windows.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-06T00:00:00+00:00",
                "windows": {
                    "audit-b": {"pid": 1111, "hwnd": 2222, "title": "owlclaw-audit-b"},
                },
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (runtime_dir / "launch-state" / "audit-b.json").write_text(
        json.dumps(
            {
                "agent": "audit-b",
                "status": "running",
                "pid": 9999,
                "updated_at": "2026-03-06T00:00:00+00:00",
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert control._window_process_id(tmp_path, "audit-b") == 9999
    assert control._window_handle(tmp_path, "audit-b") == 2222


def test_refresh_window_binding_updates_manifest(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")

    class Result:
        returncode = 0
        stdout = json.dumps({"found": True, "title": "owlclaw-codex", "pid": 2222, "hwnd": 3333})
        stderr = ""

    control.subprocess.run = lambda *args, **kwargs: Result()
    payload = control._refresh_window_binding(tmp_path, "codex", ["owlclaw-codex"])
    assert payload == {"title": "owlclaw-codex", "pid": 2222, "hwnd": 3333}
    manifest = json.loads((tmp_path / ".kiro" / "runtime" / "terminal-windows.json").read_text(encoding="utf-8"))
    assert manifest["windows"]["codex"]["pid"] == 2222
    assert manifest["windows"]["codex"]["hwnd"] == 3333


def test_send_to_window_candidates_clears_stale_binding_on_failure(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    runtime_dir = tmp_path / ".kiro" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "terminal-windows.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-06T00:00:00+00:00",
                "windows": {
                    "audit-b": {"pid": 1111, "hwnd": 2222, "title": "owlclaw-audit-b"},
                },
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    class Result:
        def __init__(self, returncode: int, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = stderr

    calls: list[tuple[str, int | None, int | None]] = []

    def fake_send(repo_root: Path, window_title: str, message: str, *, process_id: int | None = None, window_handle: int | None = None):
        calls.append((window_title, process_id, window_handle))
        return Result(1, "window missing")

    control._send_to_window = fake_send
    control._refresh_window_binding = lambda repo_root, agent, titles, process_id=None: None
    title, result = control._send_to_window_candidates(
        tmp_path,
        ["owlclaw-audit-b"],
        "继续审计复核",
        process_id=1111,
        window_handle=2222,
    )

    assert title == "owlclaw-audit-b"
    assert result.returncode == 1
    manifest = json.loads((runtime_dir / "terminal-windows.json").read_text(encoding="utf-8"))
    assert manifest["windows"]["audit-b"]["pid"] == 0
    assert manifest["windows"]["audit-b"]["hwnd"] == 0
    assert calls[0] == ("owlclaw-audit-b", 1111, None)


def test_send_to_window_candidates_prefers_process_id_from_launch_state(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    control = _load_module("workflow_terminal_control", "scripts/workflow_terminal_control.py")
    runtime_dir = tmp_path / ".kiro" / "runtime"
    (runtime_dir / "launch-state").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "launch-state" / "audit-b.json").write_text(
        json.dumps(
            {
                "agent": "audit-b",
                "status": "running",
                "pid": 4321,
                "updated_at": "2026-03-06T00:00:00+00:00",
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (runtime_dir / "audit-state").mkdir(parents=True, exist_ok=True)
    (runtime_dir / "audit-state" / "audit-b.json").write_text(
        json.dumps({"agent": "audit-b", "status": "idle", "updated_at": "2026-03-06T00:00:00+00:00"}, ensure_ascii=True),
        encoding="utf-8",
    )

    calls: list[tuple[str, int | None, int | None]] = []

    class Result:
        returncode = 0
        stdout = "sent"
        stderr = ""

    def fake_send(repo_root: Path, window_title: str, message: str, *, process_id: int | None = None, window_handle: int | None = None):
        calls.append((window_title, process_id, window_handle))
        return Result()

    control._send_to_window = fake_send
    result = control.drive_once(tmp_path, "audit-b", transport="sendkeys", force=True)

    assert result["delivered"] is True
    assert result["injected"] is True
    assert calls[0] == ("owlclaw-audit-b", 4321, None)
