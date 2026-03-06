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


def test_process_once_runs_review_execution(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    invoked: dict[str, object] = {}

    def fake_invoke(repo_root: Path, agent: str, *, workdir: Path, prompt: str) -> dict[str, object]:
        invoked["agent"] = agent
        invoked["workdir"] = str(workdir)
        invoked["prompt"] = prompt
        return {
            "agent": agent,
            "runner": "claude",
            "executed_at": "2026-03-06T00:00:01+00:00",
            "workdir": str(workdir),
            "command": ["codex", "exec"],
            "returncode": 0,
            "last_message_path": str(tmp_path / "last.txt"),
            "log_path": str(tmp_path / "log.txt"),
            "last_message": "review complete",
            "error_kind": "",
        }

    executor_module._invoke_runner = fake_invoke
    result = executor_module.process_once(tmp_path, "review")

    assert result["status"] == "done"
    assert result["executed"] is True
    assert invoked["agent"] == "review"
    assert str(invoked["prompt"]) == "继续审校。只审 codex-work 和 codex-gpt-work 的代码提交，不审计审计报告。直接执行，不要反问。"

    ack = mailbox_module.read_ack(tmp_path, "review")
    assert ack is not None
    assert ack["status"] == "done"


def test_process_once_idles_when_no_executable_action(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "codex",
        "action": "wait_for_review",
        "summary": "Stop coding and wait for review-work verdict.",
        "pending_commits": [],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "codex.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    executor_module._invoke_runner = lambda *args, **kwargs: {
        "agent": "codex",
        "runner": "agent",
        "executed_at": "2026-03-06T00:00:01+00:00",
        "workdir": str(tmp_path),
        "command": ["agent"],
        "returncode": 0,
        "last_message_path": str(tmp_path / "last.txt"),
        "log_path": str(tmp_path / "log.txt"),
        "last_message": "waiting for review",
        "error_kind": "",
    }
    result = executor_module.process_once(tmp_path, "codex")
    assert result["status"] == "done"
    assert result["executed"] is True


def test_process_once_skips_already_processed_mailbox(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    fingerprint = executor_module._mailbox_fingerprint(mailbox_payload)
    state_path = tmp_path / ".kiro" / "runtime" / "executor-state" / "review.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "agent": "review",
                "updated_at": "2026-03-06T00:00:01+00:00",
                "fingerprint": fingerprint,
                "status": "done",
                "action": "review_pending_commits",
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = executor_module.process_once(tmp_path, "review")
    assert result["executed"] is False
    assert result["reason"] == "already_processed"


def test_invoke_runner_uses_wrapper_when_direct_command_missing(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    original_which = executor_module.shutil.which
    original_run = executor_module.subprocess.run

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    calls: list[list[str]] = []

    def fake_which(name: str):
        mapping = {
            "codex": None,
            "codex.ps1": "C:\\Users\\yeemi\\AppData\\Roaming\\npm\\codex.ps1",
            "pwsh": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        }
        return mapping.get(name)

    def fake_run(command, **kwargs):
        calls.append(command)
        last_message_path = Path(command[-2])
        last_message_path.write_text("ok", encoding="utf-8")
        return Result()

    executor_module.shutil.which = fake_which
    executor_module.subprocess.run = fake_run
    try:
        result = executor_module._invoke_runner(tmp_path, "main", workdir=tmp_path, prompt="hello")
    finally:
        executor_module.shutil.which = original_which
        executor_module.subprocess.run = original_run

    assert calls
    assert calls[0][:3] == ["C:\\Program Files\\PowerShell\\7\\pwsh.exe", "-File", "C:\\Users\\yeemi\\AppData\\Roaming\\npm\\codex.ps1"]
    assert result["returncode"] == 0


def test_invoke_runner_supports_agent_backend(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    original_which = executor_module.shutil.which
    original_run = executor_module.subprocess.run

    class Result:
        returncode = 0
        stdout = json.dumps({"type": "result", "result": "agent completed"})
        stderr = ""

    calls: list[list[str]] = []

    def fake_which(name: str):
        mapping = {
            "agent": None,
            "agent.ps1": "C:\\Users\\yeemi\\AppData\\Local\\cursor-agent\\agent.ps1",
            "pwsh": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        }
        return mapping.get(name)

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    executor_module.shutil.which = fake_which
    executor_module.subprocess.run = fake_run
    try:
        result = executor_module._invoke_runner(tmp_path, "codex", workdir=tmp_path, prompt="hello")
    finally:
        executor_module.shutil.which = original_which
        executor_module.subprocess.run = original_run

    assert calls
    assert calls[0][:3] == ["C:\\Program Files\\PowerShell\\7\\pwsh.exe", "-File", "C:\\Users\\yeemi\\AppData\\Local\\cursor-agent\\agent.ps1"]
    assert result["runner"] == "agent"
    assert result["last_message"] == "agent completed"


def test_mailbox_fingerprint_ignores_generated_at() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")

    first = {
        "generated_at": "2026-03-06T00:00:00+00:00",
        "action": "review_pending_commits",
        "stage": "review",
        "summary": "x",
        "pending_commits": ["a"],
        "blockers": [],
        "dirty_files": [],
    }
    second = {**first, "generated_at": "2026-03-06T00:01:00+00:00"}
    assert executor_module._mailbox_fingerprint(first) == executor_module._mailbox_fingerprint(second)


def test_detect_invalid_output_flags_ready_reply() -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    assert executor_module._detect_invalid_output("What would you like me to work on next?") == "non_executing_reply"


def test_process_once_marks_timeout_blocked(tmp_path: Path) -> None:
    mailbox_module = _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    executor_module = _load_module("workflow_executor", "scripts/workflow_executor.py")
    mailbox_module.ensure_runtime_dirs(tmp_path)

    mailbox_payload = {
        "mailbox_version": 1,
        "generated_at": "2026-03-06T00:00:00+00:00",
        "agent": "review",
        "action": "review_pending_commits",
        "summary": "Review pending coding submissions in order: codex-work.",
        "pending_commits": ["eb308ad D12/D15/D16/D21"],
        "blockers": [],
        "dirty_files": [],
    }
    mailbox_path = tmp_path / ".kiro" / "runtime" / "mailboxes" / "review.json"
    mailbox_path.write_text(json.dumps(mailbox_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def fake_invoke(*args, **kwargs):
        raise executor_module.subprocess.TimeoutExpired(cmd=["claude"], timeout=120)

    executor_module._invoke_runner = fake_invoke
    result = executor_module.process_once(tmp_path, "review")
    assert result["status"] == "blocked"
    assert result["result"]["error_kind"] == "timeout"
