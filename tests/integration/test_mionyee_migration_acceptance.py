"""Integration check for mionyee final migration acceptance report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_mionyee_migration_acceptance_script_generates_passing_report() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "mionyee_migration_acceptance.py"
    output = repo / ".kiro" / "specs" / "mionyee-hatchet-migration" / "final_acceptance_report.json"

    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["gate"]["passed"] is True
    assert payload["recovery"]["recovered"] is True
    assert payload["rollback_verified"] is True
