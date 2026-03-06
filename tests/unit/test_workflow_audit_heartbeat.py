from __future__ import annotations

import importlib.util
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


def test_audit_heartbeat_once_writes_state(tmp_path: Path) -> None:
    _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")
    heartbeat = _load_module("workflow_audit_heartbeat", "scripts/workflow_audit_heartbeat.py")

    exit_code = heartbeat.main(
        [
            "--repo-root",
            str(tmp_path),
            "--agent",
            "audit-a",
            "--status",
            "started",
            "--summary",
            "heartbeat test",
            "--finding-ref",
            "D48",
            "--once",
        ]
    )

    assert exit_code == 0
    state_module = sys.modules["workflow_audit_state"]
    payload = state_module.read_state(tmp_path, "audit-a")
    assert payload is not None
    assert payload["status"] == "started"
    assert payload["finding_ref"] == "D48"
