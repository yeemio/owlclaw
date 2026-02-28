"""Reproducibility checks for content article code sample."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_openclaw_one_command_demo_runs_once() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        "poetry",
        "run",
        "python",
        "docs/content/snippets/openclaw_one_command_demo.py",
        "--once",
    ]
    result = subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout.strip())
    assert payload["runtime_initialized"] is True
    assert payload["step_1_install"] is True
    assert payload["step_2_configure"] is True
    assert payload["step_3_use"] is True
    assert payload["result"]["status"] == "ok"
