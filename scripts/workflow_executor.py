"""Execute mailbox actions by invoking Codex non-interactively inside each worktree."""

from __future__ import annotations

import argparse
import json
import locale
import os
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
import workflow_assignments  # noqa: E402
import workflow_objects  # noqa: E402
import workflow_roles  # noqa: E402

PROMPT_VERSION = 4
RUNNER_TIMEOUT_SECONDS = 120
LONG_RUNNING_TIMEOUT_SECONDS = 600
TRIAGE_TIMEOUT_SECONDS = 300
DEFAULT_LEASE_SECONDS = 900


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
        "object_type": mailbox.get("object_type"),
        "object_id": mailbox.get("object_id"),
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
    role_contract = str(mailbox.get("role_contract") or workflow_roles.role_contract(agent)["contract"]).strip()

    def _with_role(text: str) -> str:
        if not role_contract:
            return text
        return f"{role_contract} {text}"

    if action == "review_pending_commits" and agent == "review":
        return _with_role("继续审校。只审 codex-work 和 codex-gpt-work 的代码提交，不审计审计报告。直接执行，不要反问。")

    if action == "idle" and agent == "review":
        return _with_role("继续审校。当前没有待审 delivery 或 coding 提交时，只汇报 idle 并保持待命，不要反问。")

    if action == "cleanup_or_commit_local_changes" and agent in {"codex", "codex-gpt"}:
        return _with_role("继续spec循环。先处理并收口你当前 worktree 的未提交改动，直接执行，不要反问。")

    if action == "wait_for_review" and agent in {"codex", "codex-gpt"}:
        return _with_role("继续spec循环。如果当前确实应等待审校，就只汇报等待审校且不要反问。")

    if action == "wait_for_assignment" and agent in {"codex", "codex-gpt"}:
        return _with_role("继续spec循环。当前没有 assignment 时只汇报等待分配并保持待命，不要反问。")

    if action == "execute_assignment" and agent in {"codex", "codex-gpt"}:
        return _with_role("继续spec循环。执行当前 assignment，完成后回写 delivery，不要反问。")

    if action == "merge_review_work" and agent == "main":
        return _with_role("统筹。直接推进当前 merge/sync/分配动作，不要反问。")

    if action == "clean_local_changes" and agent == "main":
        return _with_role("统筹。先处理 main 当前阻塞，再继续后续动作，不要反问。")

    if action == "hold_merge_and_wait_for_rework" and agent == "main":
        return _with_role("统筹。当前禁止 merge；先处理 reject/rework 阻塞并等待 coding 分支收口，不要反问。")

    if action == "assign_next_batch" and agent == "main":
        return _with_role("统筹。当前 review 和 coding 队列已清空，直接执行下一批 assignment/分配动作，不要反问。")

    if action == "monitor" and agent == "main":
        return _with_role("统筹。检查当前 workflow objects、mailbox、stalled 状态；如果没有可执行动作就明确汇报 monitor，不要反问。")

    if action == "process_triage" and agent == "main":
        return _with_role("统筹。处理当前 triage 队列，为 findings 生成明确分配，不要反问。")

    if action == "process_verdict" and agent == "main":
        return _with_role("统筹。处理当前 review verdict，生成 merge 或重新分配决策，不要反问。")

    if action == "apply_merge_decision" and agent == "main":
        return _with_role("统筹。执行当前 merge_decision，完成对象链条收口或重新分配，不要反问。")

    if action == "review_delivery" and agent == "review":
        return _with_role("继续审校。审查当前 delivery 并写出结构化 verdict；若发现新问题，必须写回 findings，不要反问。")

    if action == "wait_for_rework_submissions" and agent == "review":
        return _with_role("继续审校。当前等待 coding 分支基于 REJECT 重新提交；保持待命并监控新 delivery，不要反问。")

    if action == "consume_reject_cleanup_and_sync_main" and agent in {"codex", "codex-gpt"}:
        return _with_role("继续spec循环。先消费当前 REJECT，清理本地改动并同步 main，然后只重做被拒绝的安全基线，不要反问。")

    return None


def _passive_action_resolution(agent: str, mailbox: dict[str, object]) -> dict[str, str] | None:
    action = str(mailbox.get("action", ""))
    dirty_files = mailbox.get("dirty_files") or []

    if action == "idle" and agent == "review":
        return {
            "status": "idle",
            "note": "review idle with no pending delivery or commit",
            "reason": "idle_review_queue_empty",
        }

    if action == "wait_for_rework_submissions" and agent == "review":
        return {
            "status": "idle",
            "note": "review is waiting for rework submissions after reject verdicts",
            "reason": "waiting_for_rework_submissions",
        }

    if action == "review_pending_commits" and agent == "review" and dirty_files:
        return {
            "status": "blocked",
            "note": "review worktree has local changes and must be cleaned before reviewing pending commits",
            "reason": "review_local_changes",
        }

    if action == "wait_for_review" and agent in {"codex", "codex-gpt"}:
        return {
            "status": "idle",
            "note": "coding branch is waiting for review",
            "reason": "waiting_for_review",
        }

    if action == "wait_for_assignment" and agent in {"codex", "codex-gpt"}:
        return {
            "status": "idle",
            "note": "coding branch is waiting for assignment",
            "reason": "waiting_for_assignment",
        }

    if action == "clean_local_changes" and agent == "main":
        return {
            "status": "blocked",
            "note": "main worktree has local changes and requires cleanup before merge/sync",
            "reason": "main_local_changes",
        }

    if action == "monitor" and agent == "main":
        return {
            "status": "idle",
            "note": "monitoring workflow state with no active decision object",
            "reason": "monitor_only",
        }

    if action == "hold_merge_and_wait_for_rework" and agent == "main":
        return {
            "status": "blocked",
            "note": "main is waiting for coding rework before merge can resume",
            "reason": "waiting_for_rework_before_merge",
        }

    return None


def _parse_review_message(message: str, delivery: dict[str, object]) -> dict[str, object]:
    default_payload = {
        "verdict": "APPROVE",
        "merge_ready": True,
        "notes": message or "review completed",
        "new_findings": [],
    }
    if not message.strip():
        return default_payload
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return default_payload
    if not isinstance(payload, dict):
        return default_payload
    verdict = str(payload.get("verdict", "APPROVE")).upper()
    if verdict not in {"APPROVE", "FIX_NEEDED", "REJECT"}:
        verdict = "APPROVE"
    merge_ready = bool(payload.get("merge_ready", verdict == "APPROVE"))
    notes = str(payload.get("notes", message or "review completed"))
    new_findings = payload.get("new_findings", [])
    if not isinstance(new_findings, list):
        new_findings = []
    normalized_findings: list[dict[str, object]] = []
    for index, item in enumerate(new_findings):
        if not isinstance(item, dict):
            continue
        normalized_findings.append(
            {
                "title": str(item.get("title", f"Review finding {index + 1}")),
                "summary": str(item.get("summary", notes)),
                "severity": str(item.get("severity", "medium")),
                "refs": {
                    "spec": str(item.get("spec", "")),
                    "task_ref": str(item.get("task_ref", "")),
                },
                "proposed_assignment": {
                    "target_agent": str(item.get("target_agent", delivery.get("branch", "")).replace("-work", "")),
                    "target_branch": str(item.get("target_branch", delivery.get("branch", ""))),
                },
            }
        )
    return {
        "verdict": verdict,
        "merge_ready": merge_ready,
        "notes": notes,
        "new_findings": normalized_findings,
    }


def _find_existing_assignment(
    repo_root: Path,
    *,
    finding_id: str,
    target_agent: str,
    target_branch: str,
    spec_name: str,
) -> dict[str, object] | None:
    for assignment in workflow_objects.list_objects(repo_root, "assignment"):
        if finding_id and finding_id not in assignment.get("finding_ids", []):
            continue
        if assignment.get("target_agent") != target_agent:
            continue
        if assignment.get("target_branch") != target_branch:
            continue
        if assignment.get("spec") != spec_name:
            continue
        return assignment
    return None


def _find_existing_delivery(repo_root: Path, assignment_id: str) -> dict[str, object] | None:
    for delivery in workflow_objects.list_objects(repo_root, "delivery"):
        if delivery.get("assignment_id") == assignment_id:
            return delivery
    return None


def _find_existing_verdict(repo_root: Path, delivery_id: str) -> dict[str, object] | None:
    for verdict in workflow_objects.list_objects(repo_root, "review_verdict"):
        if verdict.get("delivery_id") == delivery_id:
            return verdict
    return None


def _find_existing_merge_decision(repo_root: Path, verdict_id: str) -> dict[str, object] | None:
    for merge in workflow_objects.list_objects(repo_root, "merge_decision"):
        if merge.get("verdict_id") == verdict_id:
            return merge
    return None


def _last_message_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "last_message.txt"


def _log_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "codex_exec.log"


def _result_path(repo_root: Path, agent: str) -> Path:
    return _run_dir(repo_root, agent) / "result.json"


def _timeout_for_action(agent: str, mailbox: dict[str, object]) -> int:
    action = str(mailbox.get("action", ""))
    if agent == "review" and action == "review_pending_commits":
        return LONG_RUNNING_TIMEOUT_SECONDS
    if agent == "main" and action in {"process_triage", "process_verdict", "apply_merge_decision"}:
        return TRIAGE_TIMEOUT_SECONDS
    return RUNNER_TIMEOUT_SECONDS


def _cli_command_prefix(name: str) -> list[str]:
    path_entries = [Path(entry) for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    powershell_wrapper = next(
        (candidate for entry in path_entries if (candidate := entry / f"{name}.ps1").exists()),
        None,
    )
    if powershell_wrapper is not None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell:
            return [shell, "-File", str(powershell_wrapper)]
    direct = shutil.which(name)
    if direct:
        suffix = Path(direct).suffix.lower()
        if suffix in {".cmd", ".bat"}:
            return [str(Path(shutil.which("cmd") or "cmd.exe")), "/d", "/s", "/c", direct]
        return [direct]
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
        "what do you want to work on",
        "what do you want me to work on",
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
    timeout_seconds: int = RUNNER_TIMEOUT_SECONDS,
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
        timeout=timeout_seconds,
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

    try:
        mailbox = workflow_mailbox.read_mailbox(repo_root, agent)
    except FileNotFoundError:
        _save_state(
            repo_root,
            agent,
            {
                "agent": agent,
                "updated_at": _utc_now(),
                "fingerprint": "",
                "status": "idle",
                "action": "",
                "reason": "mailbox_missing",
            },
        )
        return {
            "agent": agent,
            "mailbox": None,
            "status": "idle",
            "executed": False,
            "reason": "mailbox_missing",
        }
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

    passive = _passive_action_resolution(agent, mailbox)
    if passive is not None:
        workflow_mailbox.write_ack(repo_root, agent, status=passive["status"], note=passive["note"])
        _save_state(
            repo_root,
            agent,
            {
                "agent": agent,
                "updated_at": _utc_now(),
                "fingerprint": fingerprint,
                "status": passive["status"],
                "action": mailbox.get("action", ""),
            },
        )
        return {
            "agent": agent,
            "mailbox": mailbox,
            "status": passive["status"],
            "executed": False,
            "reason": passive["reason"],
        }

    prompt = _action_prompt(agent, mailbox)

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
    object_type = str(mailbox.get("object_type", ""))
    object_id = str(mailbox.get("object_id", ""))
    if object_type == "assignment" and object_id and mailbox.get("action") == "execute_assignment":
        current = workflow_objects.read_object(repo_root, "assignment", object_id)
        if current["status"] == "pending":
            workflow_objects.update_object_status(
                repo_root,
                "assignment",
                object_id,
                new_status="claimed",
                actor=agent,
                reason="executor claimed assignment",
            )
            workflow_objects.claim_object(
                repo_root,
                "assignment",
                object_id,
                actor=agent,
                lease_seconds=DEFAULT_LEASE_SECONDS,
            )
        current = workflow_objects.read_object(repo_root, "assignment", object_id)
        if current["status"] == "claimed":
            workflow_objects.update_object_status(
                repo_root,
                "assignment",
                object_id,
                new_status="in_progress",
                actor=agent,
                reason="executor started assignment",
            )
        workflow_objects.refresh_object_claim(repo_root, "assignment", object_id, actor=agent)
    try:
        result = _invoke_runner(
            repo_root,
            agent,
            workdir=workdir,
            prompt=prompt,
            timeout_seconds=_timeout_for_action(agent, mailbox),
        )
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
    if final_status == "done":
        if object_type == "triage_decision" and object_id and mailbox.get("action") == "process_triage":
            triage = workflow_objects.read_object(repo_root, "triage_decision", object_id)
            finding_id = str((triage.get("finding_ids") or [""])[0])
            finding = workflow_objects.read_object(repo_root, "finding", finding_id) if finding_id else {}
            proposed = finding.get("proposed_assignment", {}) if isinstance(finding, dict) else {}
            spec_name = str(finding.get("refs", {}).get("spec", "")) if isinstance(finding, dict) else ""
            target_agent = str(proposed.get("target_agent", ""))
            target_branch = str(proposed.get("target_branch", ""))
            allowed, reason = workflow_assignments.validate_assignment_target(
                repo_root,
                target_agent=target_agent,
                target_branch=target_branch,
                spec_name=spec_name,
            )
            if not allowed:
                workflow_objects.create_object(
                    repo_root,
                    "blocker",
                    payload={
                        "status": "open",
                        "owner": "main",
                        "source_type": "triage_decision",
                        "source_id": object_id,
                        "summary": reason,
                    },
                )
                workflow_objects.update_object_status(
                    repo_root,
                    "triage_decision",
                    object_id,
                    new_status="deferred",
                    actor=agent,
                    reason=reason,
                )
                if finding_id:
                    workflow_objects.update_object_status(
                        repo_root,
                        "finding",
                        finding_id,
                        new_status="deferred",
                        actor=agent,
                        reason=reason,
                    )
                workflow_mailbox.write_ack(
                    repo_root,
                    agent,
                    status="blocked",
                    note=f"workflow_executor rejected triage: {reason}",
                    commit_ref=result.get("last_message_path", ""),
                )
                _save_state(
                    repo_root,
                    agent,
                    {
                        "agent": agent,
                        "updated_at": _utc_now(),
                        "fingerprint": fingerprint,
                        "status": "blocked",
                        "action": mailbox.get("action", ""),
                        "result_path": str(_result_path(repo_root, agent)),
                    },
                )
                return {
                    "agent": agent,
                    "mailbox": mailbox,
                    "status": "blocked",
                    "executed": True,
                    "result": result,
                }
            assignment = _find_existing_assignment(
                repo_root,
                finding_id=finding_id,
                target_agent=target_agent,
                target_branch=target_branch,
                spec_name=spec_name,
            )
            if assignment is None:
                previous_delivery_id = str(finding.get("relations", {}).get("parent_delivery_id", "")) if isinstance(finding, dict) else ""
                previous_assignment_id = ""
                reassign_iteration = 0
                if previous_delivery_id:
                    try:
                        previous_delivery = workflow_objects.read_object(repo_root, "delivery", previous_delivery_id)
                        previous_assignment_id = str(previous_delivery.get("assignment_id", ""))
                        if previous_assignment_id:
                            previous_assignment = workflow_objects.read_object(repo_root, "assignment", previous_assignment_id)
                            reassign_iteration = int(previous_assignment.get("reassign_iteration", 0)) + 1
                    except FileNotFoundError:
                        previous_assignment_id = ""
                assignment = workflow_objects.create_object(
                    repo_root,
                    "assignment",
                    payload={
                        "status": "pending",
                        "owner": "main",
                        "target_agent": target_agent,
                        "target_branch": target_branch,
                        "spec": spec_name,
                        "task_refs": [str(finding.get("refs", {}).get("task_ref", ""))] if finding else [],
                        "finding_ids": [finding_id] if finding_id else [],
                        "acceptance": ["Complete assigned workflow task and produce structured delivery."],
                        "claim": None,
                        "previous_assignment_id": previous_assignment_id,
                        "previous_delivery_id": previous_delivery_id,
                        "reassign_iteration": reassign_iteration,
                    },
                )
            if workflow_objects.read_object(repo_root, "triage_decision", object_id)["status"] == "pending":
                workflow_objects.update_object_status(
                    repo_root,
                    "triage_decision",
                    object_id,
                    new_status="accepted",
                    actor=agent,
                    reason=f"assignment created: {assignment['id']}",
                )
            if finding_id:
                current_finding = workflow_objects.read_object(repo_root, "finding", finding_id)
                if current_finding["status"] == "new":
                    workflow_objects.update_object_status(
                        repo_root,
                        "finding",
                        finding_id,
                        new_status="triaged",
                        actor=agent,
                        reason=f"triage accepted via {object_id}",
                    )
                    current_finding = workflow_objects.read_object(repo_root, "finding", finding_id)
                if current_finding["status"] == "triaged":
                    workflow_objects.update_object_status(
                        repo_root,
                        "finding",
                        finding_id,
                        new_status="assigned",
                        actor=agent,
                        reason=f"assignment created via {assignment['id']}",
                    )
        elif object_type == "assignment" and object_id and mailbox.get("action") == "execute_assignment":
            delivery = _find_existing_delivery(repo_root, object_id)
            if delivery is None:
                delivery = workflow_objects.create_object(
                    repo_root,
                    "delivery",
                    payload={
                        "status": "pending_review",
                        "owner": "review",
                        "assignment_id": object_id,
                        "branch": str(mailbox.get("branch", "")),
                        "commit_refs": [],
                        "changed_files": [],
                        "tests_run": [],
                        "summary": str(result.get("last_message", "")) or str(mailbox.get("summary", "")),
                        "blockers": [],
                        "claim": None,
                    },
                )
            workflow_objects.update_object_status(
                repo_root,
                "assignment",
                object_id,
                new_status="delivered",
                actor=agent,
                reason=f"delivery created: {delivery['id']}",
                extra_updates={"delivery_id": delivery["id"]},
            ) if workflow_objects.read_object(repo_root, "assignment", object_id)["status"] != "delivered" else workflow_objects.read_modify_write_object(
                repo_root,
                "assignment",
                object_id,
                updates={"delivery_id": delivery["id"]},
            )
            workflow_objects.clear_object_claim(repo_root, "assignment", object_id)
        elif object_type == "delivery" and object_id and mailbox.get("action") == "review_delivery":
            delivery = workflow_objects.read_object(repo_root, "delivery", object_id)
            existing_verdict = _find_existing_verdict(repo_root, object_id)
            if existing_verdict is None:
                parsed_review = _parse_review_message(str(result.get("last_message", "")), delivery)
                new_finding_ids: list[str] = []
                for finding_payload in parsed_review["new_findings"]:
                    finding = workflow_objects.create_object(
                        repo_root,
                        "finding",
                        payload={
                            "status": "new",
                            "owner": "main",
                            "source": "review",
                            "source_type": "review",
                            "title": finding_payload["title"],
                            "summary": finding_payload["summary"],
                            "severity": finding_payload["severity"],
                            "refs": finding_payload["refs"],
                            "relations": {
                                "parent_delivery_id": object_id,
                                "parent_verdict_id": "",
                            },
                            "proposed_assignment": finding_payload["proposed_assignment"],
                        },
                    )
                    new_finding_ids.append(str(finding["id"]))
                verdict = workflow_objects.create_object(
                    repo_root,
                    "review_verdict",
                    payload={
                        "status": "pending_main",
                        "owner": "main",
                        "delivery_id": object_id,
                        "verdict": parsed_review["verdict"],
                        "new_finding_ids": new_finding_ids,
                        "merge_ready": parsed_review["merge_ready"],
                        "notes": parsed_review["notes"],
                        "claim": None,
                    },
                )
            else:
                verdict = existing_verdict
                parsed_review = {
                    "verdict": verdict["verdict"],
                    "merge_ready": verdict["merge_ready"],
                    "notes": verdict["notes"],
                    "new_findings": [],
                }
            target_delivery_status = (
                "approved"
                if parsed_review["verdict"] == "APPROVE"
                else ("fix_needed" if parsed_review["verdict"] == "FIX_NEEDED" else "rejected")
            )
            current_delivery = workflow_objects.read_object(repo_root, "delivery", object_id)
            if current_delivery["status"] != target_delivery_status:
                workflow_objects.update_object_status(
                    repo_root,
                    "delivery",
                    object_id,
                    new_status=target_delivery_status,
                    actor=agent,
                    reason="review completed and verdict created",
                )
            assignment_id = str(delivery.get("assignment_id", ""))
            if assignment_id and parsed_review["verdict"] in {"FIX_NEEDED", "REJECT"}:
                assignment = workflow_objects.read_object(repo_root, "assignment", assignment_id)
                if assignment["status"] == "delivered":
                    workflow_objects.update_object_status(
                        repo_root,
                        "assignment",
                        assignment_id,
                        new_status="returned",
                        actor=agent,
                        reason=f"review verdict={parsed_review['verdict']}",
                    )
        elif object_type == "review_verdict" and object_id and mailbox.get("action") == "process_verdict":
            verdict = workflow_objects.read_object(repo_root, "review_verdict", object_id)
            decision = "merge_review_work" if verdict.get("verdict") == "APPROVE" and verdict.get("merge_ready") else "reassign"
            summary = (
                "Merge decision generated from review verdict."
                if decision == "merge_review_work"
                else "Reassign work based on review findings."
            )
            merge = _find_existing_merge_decision(repo_root, object_id)
            if merge is None:
                workflow_objects.create_object(
                    repo_root,
                    "merge_decision",
                    payload={
                        "status": "pending",
                        "owner": "main",
                        "verdict_id": object_id,
                        "decision": decision,
                        "summary": summary,
                    },
                )
            if workflow_objects.read_object(repo_root, "review_verdict", object_id)["status"] != "applied":
                workflow_objects.update_object_status(
                    repo_root,
                    "review_verdict",
                    object_id,
                    new_status="applied",
                    actor=agent,
                    reason="merge decision created",
                )
        elif object_type == "merge_decision" and object_id and mailbox.get("action") == "apply_merge_decision":
            merge = workflow_objects.read_object(repo_root, "merge_decision", object_id)
            verdict = workflow_objects.read_object(repo_root, "review_verdict", str(merge.get("verdict_id", "")))
            delivery = workflow_objects.read_object(repo_root, "delivery", str(verdict.get("delivery_id", "")))
            assignment_id = str(delivery.get("assignment_id", ""))
            assignment = workflow_objects.read_object(repo_root, "assignment", assignment_id) if assignment_id else {}
            if merge.get("decision") == "merge_review_work":
                workflow_objects.update_object_status(
                    repo_root,
                    "merge_decision",
                    object_id,
                    new_status="merged",
                    actor=agent,
                    reason="main applied merge decision",
                )
                workflow_objects.read_modify_write_object(
                    repo_root,
                    "delivery",
                    str(delivery["id"]),
                    updates={"merge_decision_id": object_id, "final_resolution": "merged"},
                )
                if assignment_id:
                    workflow_objects.read_modify_write_object(
                        repo_root,
                        "assignment",
                        assignment_id,
                        updates={"merge_decision_id": object_id, "final_resolution": "merged"},
                    )
                for finding_id in assignment.get("finding_ids", []) if isinstance(assignment, dict) else []:
                    finding = workflow_objects.read_object(repo_root, "finding", str(finding_id))
                    if finding["status"] == "assigned":
                        workflow_objects.update_object_status(
                            repo_root,
                            "finding",
                            str(finding_id),
                            new_status="merged",
                            actor=agent,
                            reason=f"merged via {object_id}",
                        )
            else:
                workflow_objects.update_object_status(
                    repo_root,
                    "merge_decision",
                    object_id,
                    new_status="reassigned",
                    actor=agent,
                    reason="main applied reassign decision",
                )
                workflow_objects.read_modify_write_object(
                    repo_root,
                    "delivery",
                    str(delivery["id"]),
                    updates={"merge_decision_id": object_id, "final_resolution": "reassigned"},
                )
                if assignment_id:
                    workflow_objects.read_modify_write_object(
                        repo_root,
                        "assignment",
                        assignment_id,
                        updates={"merge_decision_id": object_id, "final_resolution": "reassigned"},
                    )
    elif final_status == "blocked" and object_type == "assignment" and object_id and mailbox.get("action") == "execute_assignment":
        current = workflow_objects.read_object(repo_root, "assignment", object_id)
        if current["status"] in {"claimed", "in_progress"}:
            workflow_objects.update_object_status(
                repo_root,
                "assignment",
                object_id,
                new_status="blocked",
                actor=agent,
                reason="executor failed assignment",
            )
            workflow_objects.create_object(
                repo_root,
                "blocker",
                payload={
                    "status": "open",
                    "owner": "main",
                    "source_type": "assignment",
                    "source_id": object_id,
                    "summary": "Assignment execution failed and needs reassignment or intervention.",
                },
            )
            workflow_objects.clear_object_claim(repo_root, "assignment", object_id)
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
