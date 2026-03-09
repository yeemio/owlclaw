from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
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


def test_default_worker_specs_include_mailbox_agents(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")

    specs = module.default_worker_specs(tmp_path, interval=30)
    names = {spec.name for spec in specs}

    assert "orchestrator" in names
    assert "main-agent" in names
    assert "review-agent" in names
    assert "codex-agent" in names
    assert "codex-gpt-agent" in names
    assert "main-mailbox-agent" in names
    assert "review-mailbox-agent" in names
    assert "codex-mailbox-agent" in names
    assert "codex-gpt-mailbox-agent" in names


def test_status_all_reports_stalled_objects(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    objects = _load_module("workflow_objects", "scripts/workflow_objects.py")
    module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")

    assignment = objects.create_object(
        tmp_path,
        "assignment",
        payload={
            "status": "pending",
            "owner": "main",
            "target_agent": "codex",
            "target_branch": "codex-work",
            "spec": "audit-deep-remediation-followup",
            "task_refs": ["#47"],
            "finding_ids": ["finding-1"],
            "acceptance": ["produce delivery"],
            "claim": None,
        },
    )
    objects.claim_object(tmp_path, "assignment", assignment["id"], actor="codex", lease_seconds=1)
    objects.read_modify_write_object(
        tmp_path,
        "assignment",
        assignment["id"],
        updates={
            "claim": {
                "claimed_by": "codex",
                "claimed_at": "2026-03-06T00:00:00+00:00",
                "heartbeat_at": "2026-03-06T00:00:00+00:00",
                "lease_expires_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "lease_seconds": 1,
            }
        },
    )

    status = module.status_all(tmp_path, interval=0)

    assert "workers" in status
    assert any(item["id"] == assignment["id"] for item in status["stalled_objects"])


def test_start_all_primes_runtime_before_other_workers(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")

    started: list[str] = []
    primed: list[tuple[Path, int]] = []

    module.start_worker = lambda repo_root, spec: started.append(spec.name) or {"name": spec.name, "running": True}
    module._prime_runtime = lambda repo_root, interval: primed.append((repo_root, interval))
    module.status_all = lambda repo_root, interval: {"workers": [], "stalled_objects": []}

    module.start_all(tmp_path, interval=15)

    assert started[0] == "orchestrator"
    assert primed == [(tmp_path, 15)]
    assert "main-agent" in started[1:]


def test_start_all_stops_orchestrator_when_prime_runtime_fails(tmp_path: Path) -> None:
    _load_module("workflow_mailbox", "scripts/workflow_mailbox.py")
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    module = _load_module("workflow_supervisor", "scripts/workflow_supervisor.py")

    started: list[str] = []
    stopped: list[str] = []

    module.start_worker = lambda repo_root, spec: started.append(spec.name) or {"name": spec.name, "running": True}
    module.stop_worker = lambda repo_root, name: stopped.append(name) or {"name": name, "stopped": True}

    def _fail_prime(repo_root: Path, interval: int) -> None:
        raise RuntimeError("prime failed")

    module._prime_runtime = _fail_prime

    try:
        module.start_all(tmp_path, interval=15)
    except RuntimeError as exc:
        assert str(exc) == "prime failed"
    else:
        raise AssertionError("expected start_all to raise when runtime priming fails")

    assert started == ["orchestrator"]
    assert stopped == ["orchestrator"]
