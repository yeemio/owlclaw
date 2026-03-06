"""Semi-automatic mailbox consumer for OwlClaw workflow agents."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import workflow_mailbox  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / ".kiro" / "runtime"


def _agent_state_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "agent-state"


def _heartbeat_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "heartbeats"


def _dispatch_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "dispatch"


def ensure_agent_runtime_dirs(repo_root: Path) -> None:
    workflow_mailbox.ensure_runtime_dirs(repo_root)
    _agent_state_dir(repo_root).mkdir(parents=True, exist_ok=True)
    _heartbeat_dir(repo_root).mkdir(parents=True, exist_ok=True)
    _dispatch_dir(repo_root).mkdir(parents=True, exist_ok=True)


def _state_path(repo_root: Path, agent: str) -> Path:
    return _agent_state_dir(repo_root) / f"{agent}.json"


def _heartbeat_path(repo_root: Path, agent: str) -> Path:
    return _heartbeat_dir(repo_root) / f"{agent}.json"


def _dispatch_path(repo_root: Path, agent: str) -> Path:
    return _dispatch_dir(repo_root) / f"{agent}.md"


def _load_state(repo_root: Path, agent: str) -> dict[str, object] | None:
    path = _state_path(repo_root, agent)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(repo_root: Path, agent: str, payload: dict[str, object]) -> None:
    _state_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _mailbox_fingerprint(mailbox: dict[str, object]) -> str:
    payload = {
        "generated_at": mailbox.get("generated_at"),
        "action": mailbox.get("action"),
        "summary": mailbox.get("summary"),
        "pending_commits": mailbox.get("pending_commits"),
        "blockers": mailbox.get("blockers"),
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _extract_task_ref(mailbox: dict[str, object]) -> str:
    search_fields = list(mailbox.get("pending_commits") or [])
    summary = mailbox.get("summary")
    if isinstance(summary, str):
        search_fields.append(summary)
    pattern = re.compile(r"\bD\d+\b")
    for value in search_fields:
        match = pattern.search(str(value))
        if match:
            return match.group(0)
    return ""


def _dispatch_prompt(agent: str, mailbox: dict[str, object]) -> str:
    action = mailbox.get("action", "")
    summary = mailbox.get("summary", "")
    pending_commits = mailbox.get("pending_commits") or []
    blockers = mailbox.get("blockers") or []

    lines = [
        f"# Agent Dispatch: {agent}",
        "",
        f"- generated_at: {mailbox.get('generated_at', '')}",
        f"- stage: {mailbox.get('stage', '')}",
        f"- action: {action}",
        f"- priority: {mailbox.get('priority', '')}",
        "",
        "## Summary",
        str(summary),
    ]
    if pending_commits:
        lines.extend(["", "## Pending Commits"])
        lines.extend(f"- {item}" for item in pending_commits)
    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {item}" for item in blockers)

    lines.extend(["", "## Suggested Prompt"])
    if agent == "review":
        lines.append("审校当前 mailbox 指定的 coding branch 代码提交，只看代码、测试、spec/task 勾选一致性。")
    elif agent == "main":
        lines.append("统筹执行当前 mailbox 指令，只处理 merge/sync/cleanup，不把审计报告交给 review-work。")
    elif action == "wait_for_review":
        lines.append("当前分支等待 review-work 审校，不继续重叠开发；仅在需要时回执 waiting_review。")
    elif action == "cleanup_or_commit_local_changes":
        lines.append("先收口本地未提交改动，再继续本轮分配任务。")
    else:
        lines.append("按 mailbox summary 执行当前任务，并在阶段变化时回执 started/blocked/done。")

    lines.extend(
        [
            "",
            "## Ack Commands",
            (
                f"poetry run python scripts/workflow_mailbox.py ack --agent {agent} "
                "--status started --note \"picked up mailbox\""
            ),
            (
                f"poetry run python scripts/workflow_mailbox.py ack --agent {agent} "
                "--status blocked --note \"explain blocker\""
            ),
            (
                f"poetry run python scripts/workflow_mailbox.py ack --agent {agent} "
                "--status done --note \"completed current action\""
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _write_dispatch(repo_root: Path, agent: str, mailbox: dict[str, object]) -> Path:
    path = _dispatch_path(repo_root, agent)
    path.write_text(_dispatch_prompt(agent, mailbox), encoding="utf-8")
    return path


def _write_heartbeat(
    repo_root: Path,
    agent: str,
    *,
    mailbox: dict[str, object],
    ack: dict[str, object] | None,
    changed: bool,
) -> dict[str, object]:
    payload = {
        "agent": agent,
        "pid": os.getpid(),
        "polled_at": _utc_now(),
        "mailbox_generated_at": mailbox.get("generated_at", ""),
        "mailbox_action": mailbox.get("action", ""),
        "mailbox_priority": mailbox.get("priority", ""),
        "mailbox_changed": changed,
        "ack_status": ack.get("status", "") if ack else "",
        "ack_at": ack.get("acked_at", "") if ack else "",
    }
    _heartbeat_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def process_once(
    repo_root: Path,
    agent: str,
    *,
    auto_ack_seen: bool = True,
) -> dict[str, object]:
    workflow_mailbox._validate_agent(agent)
    ensure_agent_runtime_dirs(repo_root)

    mailbox = workflow_mailbox.read_mailbox(repo_root, agent)
    previous = _load_state(repo_root, agent)
    fingerprint = _mailbox_fingerprint(mailbox)
    changed = previous is None or previous.get("fingerprint") != fingerprint

    ack_payload = workflow_mailbox.read_ack(repo_root, agent)
    if changed and auto_ack_seen:
        ack_payload = workflow_mailbox.write_ack(
            repo_root,
            agent,
            status="seen",
            note="mailbox received by workflow_agent",
            task_ref=_extract_task_ref(mailbox),
        )

    dispatch_path = _write_dispatch(repo_root, agent, mailbox)
    heartbeat = _write_heartbeat(repo_root, agent, mailbox=mailbox, ack=ack_payload, changed=changed)
    _save_state(
        repo_root,
        agent,
        {
            "agent": agent,
            "updated_at": _utc_now(),
            "fingerprint": fingerprint,
            "mailbox_generated_at": mailbox.get("generated_at", ""),
            "last_action": mailbox.get("action", ""),
            "last_ack_status": ack_payload.get("status", "") if ack_payload else "",
        },
    )

    return {
        "agent": agent,
        "changed": changed,
        "dispatch_path": str(dispatch_path),
        "mailbox": mailbox,
        "ack": ack_payload,
        "heartbeat": heartbeat,
    }


def _render_update(result: dict[str, object]) -> str:
    mailbox = result["mailbox"]
    lines = [
        f"[{result['agent']}] action={mailbox.get('action', '')} priority={mailbox.get('priority', '')}",
        f"summary: {mailbox.get('summary', '')}",
        f"dispatch: {result['dispatch_path']}",
    ]
    ack = result.get("ack")
    if ack:
        lines.append(f"ack: {ack.get('status', '')} at {ack.get('acked_at', '')}")
    if result["changed"]:
        lines.append("mailbox changed: yes")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume workflow mailboxes and emit semi-automatic dispatch prompts.")
    parser.add_argument("--repo-root", default=".", help="Path to the main repository root.")
    parser.add_argument("--agent", required=True, choices=sorted(workflow_mailbox.VALID_AGENT_NAMES))
    parser.add_argument("--once", action="store_true", help="Run one mailbox poll and exit.")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds.")
    parser.add_argument(
        "--auto-ack-seen",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically write ack=seen when a mailbox change is detected.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--quiet-unchanged",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Suppress text output when mailbox content is unchanged.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    while True:
        result = process_once(repo_root, args.agent, auto_ack_seen=args.auto_ack_seen)
        if args.json:
            if not args.quiet_unchanged or result["changed"]:
                print(json.dumps(result, ensure_ascii=True, indent=2))
        elif not args.quiet_unchanged or result["changed"]:
            print(_render_update(result))

        if args.once:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
