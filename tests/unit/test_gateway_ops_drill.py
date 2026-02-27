"""Smoke test for scripts/gateway_ops_drill.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_gateway_ops_drill_script_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "gateway_ops_drill.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = repo / "docs" / "ops" / "reports" / "gateway-ops-drill-latest.md"
    assert report.exists()
    payload = report.read_text(encoding="utf-8")
    assert "canary_auto_rollback=true: true" in payload
    assert "full_rollout_success=true: true" in payload
