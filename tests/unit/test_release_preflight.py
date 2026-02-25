"""Tests for release preflight script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_release_preflight_script_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "release_preflight.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "owlclaw_version=" in result.stdout
    assert "skill_list_ok=true" in result.stdout

