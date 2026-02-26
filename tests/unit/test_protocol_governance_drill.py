"""Smoke test for scripts/protocol_governance_drill.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_protocol_governance_drill_script_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "protocol_governance_drill.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = repo / "docs" / "protocol" / "reports" / "governance-drill-latest.md"
    assert report.exists()
    payload = report.read_text(encoding="utf-8")
    assert "breaking_blocked=true: true" in payload
    assert "exemption_audited=true: true" in payload
