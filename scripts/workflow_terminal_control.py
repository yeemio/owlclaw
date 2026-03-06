"""Drive already-open terminal windows by sending fixed workflow utterances."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import workflow_mailbox  # noqa: E402


TITLE_MAP = {
    "main": ["owlclaw-main"],
    "review": ["owlclaw-review", "claude"],
    "codex": ["owlclaw-codex"],
    "codex-gpt": ["owlclaw-codex-gpt"],
    "audit-a": ["owlclaw-audit-a"],
    "audit-b": ["owlclaw-audit-b"],
}
MAILBOX_AGENTS = sorted(workflow_mailbox.VALID_AGENT_NAMES)
ALL_TERMINAL_TARGETS = MAILBOX_AGENTS + ["audit-a", "audit-b"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / ".kiro" / "runtime"


def _state_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "terminal-control"


def _audit_state_path(repo_root: Path, agent: str) -> Path:
    return _runtime_dir(repo_root) / "audit-state" / f"{agent}.json"


def _heartbeat_path(repo_root: Path, agent: str) -> Path:
    return _runtime_dir(repo_root) / "heartbeats" / f"{agent}.json"


def _ack_path(repo_root: Path, agent: str) -> Path:
    return _runtime_dir(repo_root) / "acks" / f"{agent}.json"


def _window_manifest_path(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "terminal-windows.json"


def _pause_flag_path(repo_root: Path) -> Path:
    return _state_dir(repo_root) / "paused.flag"


def ensure_dirs(repo_root: Path) -> None:
    workflow_mailbox.ensure_runtime_dirs(repo_root)
    _state_dir(repo_root).mkdir(parents=True, exist_ok=True)


def _state_path(repo_root: Path, agent: str) -> Path:
    return _state_dir(repo_root) / f"{agent}.json"


def _load_state(repo_root: Path, agent: str) -> dict[str, object] | None:
    path = _state_path(repo_root, agent)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(repo_root: Path, agent: str, payload: dict[str, object]) -> None:
    _state_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _save_window_manifest(repo_root: Path, manifest: dict[str, object]) -> None:
    path = _window_manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")


def is_paused(repo_root: Path) -> bool:
    ensure_dirs(repo_root)
    return _pause_flag_path(repo_root).exists()


def set_paused(repo_root: Path, paused: bool) -> None:
    ensure_dirs(repo_root)
    flag = _pause_flag_path(repo_root)
    if paused:
        flag.write_text("paused\n", encoding="utf-8")
        return
    if flag.exists():
        flag.unlink()


def _fingerprint(mailbox: dict[str, object], message: str) -> str:
    payload = {
        "action": mailbox.get("action"),
        "stage": mailbox.get("stage"),
        "summary": mailbox.get("summary"),
        "pending_commits": mailbox.get("pending_commits"),
        "dirty_files": mailbox.get("dirty_files"),
        "message": message,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _load_window_manifest(repo_root: Path) -> dict[str, object]:
    path = _window_manifest_path(repo_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso8601(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(value: object) -> float | None:
    dt = _parse_iso8601(value)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()


def _window_process_id(repo_root: Path, agent: str) -> int | None:
    manifest = _load_window_manifest(repo_root)
    windows = manifest.get("windows", {})
    if not isinstance(windows, dict):
        return None
    payload = windows.get(agent)
    if not isinstance(payload, dict):
        return None
    pid = payload.get("pid")
    return pid if isinstance(pid, int) and pid > 0 else None


def _window_handle(repo_root: Path, agent: str) -> int | None:
    manifest = _load_window_manifest(repo_root)
    windows = manifest.get("windows", {})
    if not isinstance(windows, dict):
        return None
    payload = windows.get(agent)
    if not isinstance(payload, dict):
        return None
    handle = payload.get("hwnd")
    return handle if isinstance(handle, int) and handle > 0 else None


def _refresh_window_binding(repo_root: Path, agent: str, window_titles: list[str]) -> dict[str, int | str] | None:
    script_path = SCRIPT_DIR / "workflow_find_window.ps1"
    command = ["pwsh", "-NoProfile", "-File", str(script_path)]
    for title in window_titles:
        command.extend(["-WindowTitles", title])
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 and not result.stdout.strip():
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not payload.get("found"):
        return None

    manifest = _load_window_manifest(repo_root)
    windows = manifest.setdefault("windows", {})
    current = windows.get(agent, {}) if isinstance(windows, dict) else {}
    if not isinstance(current, dict):
        current = {}
    current.update(
        {
            "title": payload["title"],
            "pid": payload["pid"],
            "hwnd": payload["hwnd"],
        }
    )
    windows[agent] = current
    _save_window_manifest(repo_root, manifest)
    return {"title": payload["title"], "pid": payload["pid"], "hwnd": payload["hwnd"]}


def _message_for_mailbox(agent: str, mailbox: dict[str, object]) -> str | None:
    action = str(mailbox.get("action", ""))

    if agent == "main":
        return "统筹"
    if agent == "review":
        return "继续审校"
    if agent in {"codex", "codex-gpt"}:
        if action in {"cleanup_or_commit_local_changes", "wait_for_review", "wait_for_assignment"}:
            return "继续spec循环"
        return "继续"
    return None


def _message_for_audit(agent: str) -> str | None:
    if agent == "audit-a":
        return "继续深度审计"
    if agent == "audit-b":
        return "继续审计复核"
    return None


def _agent_runtime_status(repo_root: Path, agent: str) -> dict[str, object]:
    heartbeat = _read_json(_heartbeat_path(repo_root, agent))
    ack = _read_json(_ack_path(repo_root, agent))
    return {
        "heartbeat": heartbeat,
        "ack": ack,
        "heartbeat_age": _seconds_since(heartbeat.get("polled_at")) if heartbeat else None,
        "ack_age": _seconds_since(ack.get("acked_at")) if ack else None,
    }


def _audit_runtime_status(repo_root: Path, agent: str) -> dict[str, object] | None:
    payload = _read_json(_audit_state_path(repo_root, agent))
    if payload is None:
        return None
    return {
        "payload": payload,
        "updated_age": _seconds_since(payload.get("updated_at")),
        "status": payload.get("status", ""),
    }


def _should_send(
    repo_root: Path,
    agent: str,
    fingerprint: str,
    *,
    force: bool,
    stale_seconds: int,
    retry_seconds: int,
) -> tuple[bool, str]:
    if agent not in workflow_mailbox.VALID_AGENT_NAMES:
        audit_status = _audit_runtime_status(repo_root, agent)
        if not force and audit_status is None:
            return False, "missing_audit_state"

    previous = _load_state(repo_root, agent)
    if force:
        return True, "forced"
    if previous is None:
        return True, "first_send"
    if previous.get("fingerprint") != fingerprint:
        return True, "fingerprint_changed"

    last_attempt_value = previous.get("sent_at")
    last_attempt_age = _seconds_since(last_attempt_value) if last_attempt_value else None
    if last_attempt_age is not None and last_attempt_age < retry_seconds:
        return False, "recent_attempt"

    if agent not in workflow_mailbox.VALID_AGENT_NAMES:
        audit_status = _audit_runtime_status(repo_root, agent)
        assert audit_status is not None
        updated_age = audit_status["updated_age"]
        status = audit_status["status"]
        if updated_age is None or updated_age >= stale_seconds:
            return True, "stale_audit_state"
        if status in {"blocked", "idle"}:
            return True, f"audit_{status}"
        return False, "fresh_audit_state"

    status = _agent_runtime_status(repo_root, agent)
    heartbeat_age = status["heartbeat_age"]
    ack_age = status["ack_age"]
    ack = status["ack"] or {}
    ack_status = ack.get("status", "")

    if heartbeat_age is None:
        return True, "missing_heartbeat"
    if heartbeat_age >= stale_seconds:
        return True, "stale_heartbeat"
    if ack_age is None:
        return True, "missing_ack"
    if ack_age >= stale_seconds:
        return True, "stale_ack"
    if ack_status in {"blocked", "idle"}:
        return True, f"ack_{ack_status}"
    return False, "fresh_runtime"


def _send_to_window(
    repo_root: Path,
    window_title: str,
    message: str,
    *,
    process_id: int | None = None,
    window_handle: int | None = None,
) -> subprocess.CompletedProcess[str]:
    script_path = SCRIPT_DIR / "workflow_sendkeys.ps1"
    command = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(script_path),
        "-Message",
        message,
    ]
    if window_handle:
        command.extend(["-WindowHandle", str(window_handle)])
    if process_id:
        command.extend(["-ProcessId", str(process_id)])
    if window_title:
        command.extend(["-WindowTitle", window_title])
    return subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _send_to_window_candidates(
    repo_root: Path,
    window_titles: list[str],
    message: str,
    *,
    process_id: int | None = None,
    window_handle: int | None = None,
) -> tuple[str, subprocess.CompletedProcess[str]]:
    if window_handle or process_id:
        result = _send_to_window(
            repo_root,
            window_titles[0],
            message,
            process_id=process_id,
            window_handle=window_handle,
        )
        if result.returncode == 0:
            return window_titles[0], result
        refreshed = _refresh_window_binding(repo_root, window_titles[0].replace("owlclaw-", ""), window_titles)
        if refreshed:
            result = _send_to_window(
                repo_root,
                str(refreshed["title"]),
                message,
                process_id=int(refreshed["pid"]),
                window_handle=int(refreshed["hwnd"]),
            )
            if result.returncode == 0:
                return str(refreshed["title"]), result

    last_result: subprocess.CompletedProcess[str] | None = None
    last_title = window_titles[0]

    for title in window_titles:
        result = _send_to_window(repo_root, title, message)
        if result.returncode == 0:
            return title, result
        last_title = title
        last_result = result

    assert last_result is not None
    return last_title, last_result


def drive_once(
    repo_root: Path,
    agent: str,
    *,
    force: bool = False,
    stale_seconds: int = 180,
    retry_seconds: int = 120,
) -> dict[str, object]:
    ensure_dirs(repo_root)
    if agent in workflow_mailbox.VALID_AGENT_NAMES:
        workflow_mailbox._validate_agent(agent)
        mailbox = workflow_mailbox.read_mailbox(repo_root, agent)
        message = _message_for_mailbox(agent, mailbox)
        if not message:
            return {"agent": agent, "delivered": False, "reason": "no_message"}
    else:
        mailbox = {"action": "fixed", "stage": "fixed", "summary": "fixed audit prompt", "pending_commits": [], "dirty_files": []}
        message = _message_for_audit(agent)
        if not message:
            return {"agent": agent, "delivered": False, "reason": "unknown_agent"}

    fingerprint = _fingerprint(mailbox, message)
    should_send, reason = _should_send(
        repo_root,
        agent,
        fingerprint,
        force=force,
        stale_seconds=stale_seconds,
        retry_seconds=retry_seconds,
    )
    if not should_send:
        return {"agent": agent, "delivered": False, "reason": reason, "message": message}

    window_titles = TITLE_MAP[agent]
    process_id = _window_process_id(repo_root, agent)
    window_handle = _window_handle(repo_root, agent)
    window_title, result = _send_to_window_candidates(
        repo_root,
        window_titles,
        message,
        process_id=process_id,
        window_handle=window_handle,
    )
    delivered = result.returncode == 0
    payload = {
        "agent": agent,
        "message": message,
        "window_title": window_title,
        "delivered": delivered,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "sent_at": _utc_now(),
        "fingerprint": fingerprint,
        "decision_reason": reason,
    }
    _save_state(repo_root, agent, payload)
    return payload


def drive_all(
    repo_root: Path,
    *,
    force: bool = False,
    stale_seconds: int = 180,
    retry_seconds: int = 120,
) -> list[dict[str, object]]:
    return [
        drive_once(repo_root, agent, force=force, stale_seconds=stale_seconds, retry_seconds=retry_seconds)
        for agent in ALL_TERMINAL_TARGETS
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send fixed workflow prompts into already-open terminal windows.")
    parser.add_argument("--repo-root", default=".", help="Path to the main repository root.")
    parser.add_argument("--agent", choices=ALL_TERMINAL_TARGETS, help="Drive a single agent window.")
    parser.add_argument("--force", action="store_true", help="Resend even if the same mailbox fingerprint was already sent.")
    parser.add_argument("--once", action="store_true", help="Run one delivery pass and exit.")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds.")
    parser.add_argument("--stale-seconds", type=int, default=180, help="Treat heartbeat/ack inactivity beyond this threshold as stalled.")
    parser.add_argument("--retry-seconds", type=int, default=120, help="Minimum retry interval for the same unchanged target state.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    while True:
        if is_paused(repo_root):
            payload = {
                "paused": True,
                "sent_at": _utc_now(),
            }
        elif args.agent:
            payload = drive_once(
                repo_root,
                args.agent,
                force=args.force,
                stale_seconds=args.stale_seconds,
                retry_seconds=args.retry_seconds,
            )
        else:
            payload = drive_all(
                repo_root,
                force=args.force,
                stale_seconds=args.stale_seconds,
                retry_seconds=args.retry_seconds,
            )

        if args.json:
            print(json.dumps(payload, ensure_ascii=True, indent=2))
        else:
            print(payload)

        if args.once:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
