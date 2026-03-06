"""Execute mailbox actions by invoking Codex non-interactively inside each worktree."""

from __future__ import annotations

import argparse
import json
import locale
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import workflow_mailbox  # noqa: E402

PROMPT_VERSION = 3
RUNNER_TIMEOUT_SECONDS = 120


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / ".kiro" / "runtime"


def _execution_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "executions"


def _executor_state_dir(repo_root: Path) -> Path:
    return _runtime_dir(repo_root) / "executor-state"


def _default_workdirs(repo_root: Path) -> dict[str, Path]:
    parent = repo_root.parent
    return {
        "main": repo_root,
        "review": parent / "owlclaw-review",
        "codex": parent / "owlclaw-codex",
        "codex-gpt": parent / "owlclaw-codex-gpt",
    }


def ensure_executor_dirs(repo_root: Path) -> None:
    workflow_mailbox.ensure_runtime_dirs(repo_root)
    _execution_dir(repo_root).mkdir(parents=True, exist_ok=True)
    _executor_state_dir(repo_root).mkdir(parents=True, exist_ok=True)


def _state_path(repo_root: Path, agent: str) -> Path:
    return _executor_state_dir(repo_root) / f"{agent}.json"


def _run_dir(repo_root: Path, agent: str) -> Path:
    path = _execution_dir(repo_root) / agent
    path.mkdir(parents=True, exist_ok=True)
    return path


def _mailbox_fingerprint(mailbox: dict[str, object]) -> str:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "action": mailbox.get("action"),
        "stage": mailbox.get("stage"),
        "summary": mailbox.get("summary"),
        "pending_commits": mailbox.get("pending_commits"),
        "blockers": mailbox.get("blockers"),
        "dirty_files": mailbox.get("dirty_files"),
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _load_state(repo_root: Path, agent: str) -> dict[str, object] | None:
    path = _state_path(repo_root, agent)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(repo_root: Path, agent: str, payload: dict[str, object]) -> None:
    _state_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _action_prompt(agent: str, mailbox: dict[str, object]) -> str | None:
    action = str(mailbox.get("action", ""))
    summary = str(mailbox.get("summary", ""))
    blockers = mailbox.get("blockers") or []
    pending_commits = mailbox.get("pending_commits") or []
    dirty_files = mailbox.get("dirty_files") or []

    if action == "review_pending_commits" and agent == "review":
        commits = "\n".join(f"- {item}" for item in pending_commits) or "- none listed"
        return (
            "You are the review-work executor in D:\\AI\\owlclaw-review.\n"
            "Execute the Review Loop now. Do not reply with an acknowledgement-only message.\n"
            "Review codex-work and codex-gpt-work code submissions against main and produce actual review work.\n"
            "Do not review DEEP_AUDIT_REPORT.md itself; audit reports are owned by orchestrator/main.\n"
            "Focus on code correctness, tests, spec/task consistency, architecture compliance, and merge readiness.\n"
            "Use the repository guidance in .kiro/WORKTREE_ASSIGNMENTS.md and docs/WORKTREE_GUIDE.md.\n"
            f"Mailbox summary: {summary}\n"
            "Pending commits:\n"
            f"{commits}\n"
            "Start by inspecting git log/diff for those coding branches. Then perform the review and make the required review-work output changes in this repository.\n"
            "If the branches are ready, produce review output and apply the needed review-work changes. If blocked, explain the concrete blocker and stop.\n"
            "Do not stop after analysis if concrete review output can be produced in this run.\n"
            "Do not end with a question asking what to do next. End with concrete review results only.\n"
        )

    if action == "cleanup_or_commit_local_changes" and agent in {"codex", "codex-gpt"}:
        dirty = "\n".join(f"- {item}" for item in dirty_files) or "- no dirty files listed"
        return (
            f"You are the {agent} executor working in your assigned worktree.\n"
            "Execute the cleanup/commit task now. Do not answer with acknowledgement only.\n"
            "Your current job is to safely resolve local uncommitted changes in your own worktree.\n"
            "Inspect git status and only act on your own branch/worktree files.\n"
            "Do not touch main worktree files or unrelated audit report edits.\n"
            "If the local changes are valid current-task work, commit them with a focused message.\n"
            "If they are invalid/generated leftovers, clean them safely without disturbing user changes.\n"
            "Do not reset or discard user-owned changes outside your worktree.\n"
            f"Mailbox summary: {summary}\n"
            "Dirty files:\n"
            f"{dirty}\n"
            "When finished, leave the worktree clean and report exactly what you committed or cleaned.\n"
            "Do the work in this run; do not stop after restating the plan.\n"
        )

    if action == "merge_review_work" and agent == "main":
        return (
            "You are the main worktree executor in D:\\AI\\owlclaw.\n"
            "Execute the merge task now. Do not respond with acknowledgement only.\n"
            "Merge review-work into main if the main worktree is clean and the review branch is ready.\n"
            "Do not touch audit-report-only edits owned by the orchestrator.\n"
            f"Mailbox summary: {summary}\n"
            "Verify git status, merge review-work, resolve only safe conflicts, and report the result.\n"
        )

    return None


def _last_message_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "last_message.txt"


def _log_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "codex_exec.log"


def _result_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "result.json"


def _cli_command_prefix(name: str) -> list[str]:
    direct = shutil.which(name)
    if direct:
        return [direct]
    powershell_wrapper = shutil.which(f"{name}.ps1")
    if powershell_wrapper:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell:
            return [shell, "-File", powershell_wrapper]
    cmd_wrapper = shutil.which(f"{name}.cmd")
    if cmd_wrapper:
        return [cmd_wrapper]
    raise FileNotFoundError(f"{name} executable not found in PATH")


def _text_encoding() -> str:
    return locale.getpreferredencoding(False) or "utf-8"


def _runner_name(agent: str) -> str:
    if agent == "main":
        return "codex"
    if agent == "review":
        return "claude"
    return "agent"


def _extract_runner_message(runner: str, stdout_text: str, last_message_path: Path) -> str:
    if runner == "codex":
        if last_message_path.exists():
            return last_message_path.read_text(encoding="utf-8", errors="replace").strip()
        return ""
    if runner in {"claude", "agent"}:
        text = stdout_text.strip()
        if not text:
            return ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(payload, dict):
            result = payload.get("result", "")
            if isinstance(result, str):
                return result.strip()
        return text
    return stdout_text.strip()


def _detect_invalid_output(message: str) -> str:
    lowered = message.lower()
    invalid_markers = [
        "what would you like me to do",
        "what would you like me to work on",
        "something else you have in mind",
        "i'm ready to execute",
        "ready to execute tasks",
        "tell me whether you want",
        "send the target branch",
    ]
    for marker in invalid_markers:
        if marker in lowered:
            return "non_executing_reply"
    return ""


def _invoke_runner(
    repo_root: Path,
    agent: str,
    *,
    workdir: Path,
    prompt: str,
) -> dict[str, object]:
    log_path = _log_path(repo_root, agent)
    last_message_path = _last_message_path(repo_root, agent)
    runner = _runner_name(agent)
    if runner == "codex":
        command = [
            *_cli_command_prefix("codex"),
            "exec",
            "--cd",
            str(workdir),
            "-o",
            str(last_message_path),
            prompt,
        ]
    elif runner == "claude":
        command = [
            *_cli_command_prefix("claude"),
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "bypassPermissions",
            prompt,
        ]
    else:
        command = [
            *_cli_command_prefix("agent"),
            "--print",
            "--output-format",
            "json",
            "--force",
            "--trust",
            "--workspace",
            str(workdir),
            prompt,
        ]

    process = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding=_text_encoding(),
        errors="replace",
        check=False,
        timeout=RUNNER_TIMEOUT_SECONDS,
    )

    stdout_text = process.stdout or ""
    stderr_text = process.stderr or ""
    combined_output = stdout_text + (f"\n{stderr_text}" if stderr_text else "")
    log_path.write_text(combined_output, encoding="utf-8")

    last_message = _extract_runner_message(runner, stdout_text, last_message_path)
    if runner != "codex":
        last_message_path.write_text(last_message, encoding="utf-8")

    log_text = combined_output
    error_kind = ""
    if "You've hit your usage limit" in log_text:
        error_kind = "usage_limit"
    invalid_output = _detect_invalid_output(last_message)
    if invalid_output:
        error_kind = invalid_output

    payload = {
        "agent": agent,
        "runner": runner,
        "executed_at": _utc_now(),
        "workdir": str(workdir),
        "command": command,
        "returncode": process.returncode,
        "last_message_path": str(last_message_path),
        "log_path": str(log_path),
        "last_message": last_message,
        "error_kind": error_kind,
    }
    _result_path(repo_root, agent).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def process_once(repo_root: Path, agent: str) -> dict[str, object]:
    workflow_mailbox._validate_agent(agent)
    ensure_executor_dirs(repo_root)

    mailbox = workflow_mailbox.read_mailbox(repo_root, agent)
    prompt = _action_prompt(agent, mailbox)
    fingerprint = _mailbox_fingerprint(mailbox)
    previous = _load_state(repo_root, agent)

    if previous and previous.get("fingerprint") == fingerprint and previous.get("status") in {"done", "blocked", "idle"}:
        return {
            "agent": agent,
            "mailbox": mailbox,
            "status": previous["status"],
            "executed": False,
            "reason": "already_processed",
        }

    if prompt is None:
        status = "idle"
        workflow_mailbox.write_ack(repo_root, agent, status=status, note="no executable mailbox action")
        _save_state(
            repo_root,
            agent,
            {
                "agent": agent,
                "updated_at": _utc_now(),
                "fingerprint": fingerprint,
                "status": status,
                "action": mailbox.get("action", ""),
            },
        )
        return {"agent": agent, "mailbox": mailbox, "status": status, "executed": False, "reason": "no_action"}

    workflow_mailbox.write_ack(repo_root, agent, status="started", note="workflow_executor started mailbox action")
    workdir = _default_workdirs(repo_root)[agent]
    try:
        result = _invoke_runner(repo_root, agent, workdir=workdir, prompt=prompt)
        final_status = "done" if result["returncode"] == 0 and not result.get("error_kind") else "blocked"
    except subprocess.TimeoutExpired as exc:
        result = {
            "agent": agent,
            "runner": _runner_name(agent),
            "executed_at": _utc_now(),
            "workdir": str(workdir),
            "command": exc.cmd,
            "returncode": 124,
            "last_message_path": "",
            "log_path": str(_log_path(repo_root, agent)),
            "last_message": "",
            "error_kind": "timeout",
        }
        _result_path(repo_root, agent).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
        final_status = "blocked"
    except FileNotFoundError as exc:
        result = {
            "agent": agent,
            "runner": _runner_name(agent),
            "executed_at": _utc_now(),
            "workdir": str(workdir),
            "command": [],
            "returncode": 127,
            "last_message_path": "",
            "log_path": str(_log_path(repo_root, agent)),
            "last_message": str(exc),
        }
        _result_path(repo_root, agent).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
        final_status = "blocked"
    workflow_mailbox.write_ack(
        repo_root,
        agent,
        status=final_status,
        note=(
            "workflow_executor completed mailbox action"
            if final_status == "done"
            else (
                "workflow_executor blocked by codex usage limit"
                if result.get("error_kind") == "usage_limit"
                else (
                    "workflow_executor got non-executing reply"
                    if result.get("error_kind") == "non_executing_reply"
                    else (
                        "workflow_executor timed out"
                        if result.get("error_kind") == "timeout"
                        else "workflow_executor failed mailbox action"
                    )
                )
            )
        ),
        commit_ref=result.get("last_message_path", ""),
    )
    _save_state(
        repo_root,
        agent,
        {
            "agent": agent,
            "updated_at": _utc_now(),
            "fingerprint": fingerprint,
            "status": final_status,
            "action": mailbox.get("action", ""),
            "result_path": str(_result_path(repo_root, agent)),
        },
    )
    return {
        "agent": agent,
        "mailbox": mailbox,
        "status": final_status,
        "executed": True,
        "result": result,
    }


def _render_result(payload: dict[str, object]) -> str:
    lines = [
        f"[{payload['agent']}] status={payload['status']}",
        f"action={payload['mailbox'].get('action', '')}",
    ]
    if payload.get("executed"):
        result = payload["result"]
        lines.append(f"returncode={result['returncode']}")
        lines.append(f"log={result['log_path']}")
        lines.append(f"last_message={result['last_message_path']}")
    else:
        lines.append(f"reason={payload.get('reason', '')}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute mailbox actions through non-interactive Codex runs.")
    parser.add_argument("--repo-root", default=".", help="Path to the main repository root.")
    parser.add_argument("--agent", required=True, choices=sorted(workflow_mailbox.VALID_AGENT_NAMES))
    parser.add_argument("--once", action="store_true", help="Process one mailbox cycle and exit.")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    while True:
        payload = process_once(repo_root, args.agent)
        if args.json:
            print(json.dumps(payload, ensure_ascii=True, indent=2))
        else:
            print(_render_result(payload))
        if args.once:
            return 0
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
