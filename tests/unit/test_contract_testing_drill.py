"""Smoke test for contract-testing drill script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_contract_testing_drill_runs_and_generates_report() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "contract_diff" / "contract_testing_drill.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = repo / "docs" / "protocol" / "reports" / "contract-testing-drill-latest.md"
    assert report.exists()
    payload = report.read_text(encoding="utf-8")
    assert "additive_pass=true: true" in payload
    assert "breaking_blocked=true: true" in payload
