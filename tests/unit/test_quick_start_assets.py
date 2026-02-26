"""Quick Start assets and runnable example checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_quick_start_assets_exist() -> None:
    assert Path("docs/QUICK_START.md").exists()
    assert Path("examples/quick_start/app.py").exists()
    assert Path("examples/quick_start/SOUL.md").exists()
    assert Path("examples/quick_start/IDENTITY.md").exists()
    assert Path("examples/quick_start/skills/inventory-check/SKILL.md").exists()


def test_readme_links_quick_start_doc() -> None:
    payload = Path("README.md").read_text(encoding="utf-8")
    assert "docs/QUICK_START.md" in payload


def test_quick_start_example_once_mode_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "examples" / "quick_start" / "app.py"
    result = subprocess.run(
        [sys.executable, str(script), "--once"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert lines, result.stdout
    payload = json.loads(lines[-1])
    assert payload["status"] == "ok"
