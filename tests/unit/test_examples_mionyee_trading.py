"""Runnable checks for examples/mionyee-trading."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_mionyee_trading_example_runs_all_tasks() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "examples" / "mionyee-trading" / "app.py"
    result = subprocess.run(
        [sys.executable, str(script), "--all", "--json"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    entries = payload.get("results", [])
    assert len(entries) == 3
    assert all(item.get("status") == "passed" for item in entries)
    workflow_ids = [item.get("output", {}).get("hatchet_workflow_id") for item in entries]
    assert workflow_ids == ["wf-1", "wf-2", "wf-3"]

