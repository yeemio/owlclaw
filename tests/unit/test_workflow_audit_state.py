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


def test_write_and_read_audit_state(tmp_path: Path) -> None:
    module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")

    payload = module.write_state(
        tmp_path,
        "audit-a",
        status="started",
        summary="reviewing findings",
        finding_ref="D48",
        note="batch 1",
    )
    assert payload["status"] == "started"

    current = module.read_state(tmp_path, "audit-a")
    assert current is not None
    assert current["finding_ref"] == "D48"
    assert current["code_changes_allowed"] is False
    assert current["profile"] == "deep_audit"


def test_finding_command_creates_structured_finding(tmp_path: Path, capsys) -> None:
    _load_module("workflow_objects", "scripts/workflow_objects.py")
    module = _load_module("workflow_audit_state", "scripts/workflow_audit_state.py")

    assert (
        module.main(
            [
                "--repo-root",
                str(tmp_path),
                "finding",
                "--agent",
                "audit-a",
                "--title",
                "Audit issue",
                "--summary",
                "Observation tool exposes unsanitized args",
                "--severity",
                "p1",
                "--spec",
                "workflow-closed-loop",
                "--task-ref",
                "2.2",
                "--target-agent",
                "codex",
                "--target-branch",
                "codex-work",
                "--file",
                "owlclaw/agent/runtime/runtime.py",
                "--dimension",
                "core_logic",
                "--lens",
                "adversary",
                "--evidence",
                "Traced tool result into prompt without sanitizer in runtime._build_messages().",
                "--json",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["object_type"] == "finding"
    assert output["source"] == "audit-a"
    assert output["proposed_assignment"]["target_agent"] == "codex"
    assert output["audit_metadata"]["code_changes_allowed"] is False
