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


def test_default_worker_specs_cover_orchestrator_and_agents(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    supervisor_module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")

    specs = supervisor_module.default_worker_specs(tmp_path, 20)
    names = [spec.name for spec in specs]

    assert names == [
        "orchestrator",
        "main-agent",
        "review-agent",
        "codex-agent",
        "codex-gpt-agent",
    ]
    assert all("poetry" == spec.command[0] for spec in specs)
    assert any("workflow_orchestrator.py" in " ".join(spec.command) for spec in specs)
    assert any("--agent" in spec.command for spec in specs if spec.role == "agent")


def test_status_all_reads_manifest_and_marks_running(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    supervisor_module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")
    supervisor_module.ensure_supervisor_dirs(tmp_path)

    manifest_dir = tmp_path / ".kiro" / "runtime" / "supervisor" / "pids"
    manifest = {
        "name": "review-agent",
        "role": "agent",
        "pid": 1234,
        "started_at": "2026-03-06T00:00:00+00:00",
        "workdir": str(tmp_path / "owlclaw-review"),
        "command": ["poetry", "run", "python", "workflow_agent.py"],
        "log_path": str(tmp_path / ".kiro" / "runtime" / "supervisor" / "logs" / "review-agent.log"),
    }
    (manifest_dir / "review-agent.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")

    original = supervisor_module._is_pid_running
    supervisor_module._is_pid_running = lambda pid: pid == 1234
    try:
        statuses = supervisor_module.status_all(tmp_path, 15)
    finally:
        supervisor_module._is_pid_running = original

    review_entry = next(item for item in statuses if item["name"] == "review-agent")
    assert review_entry["running"] is True
    assert review_entry["pid"] == 1234
