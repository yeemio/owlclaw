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


def test_write_and_read_launch_state(tmp_path: Path) -> None:
    module = _load_module("workflow_launch_state", "scripts/workflow_launch_state.py")

    payload = module.write_state(tmp_path, "codex", status="starting", pid=1234, note="boot")
    assert payload["agent"] == "codex"
    assert payload["status"] == "starting"
    assert payload["pid"] == 1234

    stored = module.read_state(tmp_path, "codex")
    assert stored is not None
    assert stored["status"] == "starting"
    assert stored["note"] == "boot"


def test_exit_code_is_persisted(tmp_path: Path) -> None:
    module = _load_module("workflow_launch_state", "scripts/workflow_launch_state.py")

    module.write_state(tmp_path, "review", status="exited", pid=2222, exit_code=7)
    payload = json.loads((tmp_path / ".kiro" / "runtime" / "launch-state" / "review.json").read_text(encoding="utf-8"))
    assert payload["status"] == "exited"
    assert payload["exit_code"] == 7
