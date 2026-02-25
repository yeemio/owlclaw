"""Tests for release consistency checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_release_consistency_script_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "release_consistency_check.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "release_consistency_ok=true" in result.stdout
