"""Smoke test for scripts/validate_examples.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validate_examples_script() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "validate_examples.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["cron"]["ok"] is True
    assert payload["langchain"]["ok"] is True
    assert payload["mionyee"]["ok"] is True

