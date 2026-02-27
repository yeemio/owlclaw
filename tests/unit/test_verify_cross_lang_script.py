"""Smoke test for scripts/verify_cross_lang.ps1."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_verify_cross_lang_script_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "verify_cross_lang.ps1"
    result = subprocess.run(
        ["pwsh", "-File", str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "cross_lang_validation_ok=true" in result.stdout
    report = repo / "docs" / "protocol" / "cross_lang_validation_latest.md"
    assert report.exists()
