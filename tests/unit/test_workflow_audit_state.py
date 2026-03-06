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


def test_write_and_read_audit_state(tmp_path: Path) -> None:
    module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")

    payload = module.write_state(
        tmp_path,
        "audit-a",
        status="started",
        summary="Reviewing new findings",
        finding_ref="D48",
        note="picked up",
    )

    assert payload["agent"] == "audit-a"
    assert payload["status"] == "started"
    assert payload["finding_ref"] == "D48"

    loaded = module.read_state(tmp_path, "audit-a")
    assert loaded is not None
    assert loaded["summary"] == "Reviewing new findings"
    assert loaded["note"] == "picked up"
