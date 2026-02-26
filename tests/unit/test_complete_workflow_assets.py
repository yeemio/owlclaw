"""Complete workflow example asset checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_complete_workflow_assets_exist() -> None:
    base = Path("examples/complete_workflow")
    assert (base / "README.md").exists()
    assert (base / "app.py").exists()
    assert (base / "SOUL.md").exists()
    assert (base / "IDENTITY.md").exists()
    assert (base / "owlclaw.yaml").exists()
    assert (base / "skills/inventory-check/SKILL.md").exists()
    assert (base / "skills/reorder-decision/SKILL.md").exists()
    assert (base / "skills/anomaly-alert/SKILL.md").exists()
    assert (base / "skills/daily-report/SKILL.md").exists()
    assert (base / "handlers/inventory.py").exists()
    assert (base / "handlers/reorder.py").exists()
    assert (base / "handlers/alert.py").exists()
    assert (base / "handlers/report.py").exists()


def test_complete_workflow_once_mode_runs() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "examples" / "complete_workflow" / "app.py"
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
    decisions = payload["decisions"]
    assert "inventory-check" in decisions
    assert "reorder-decision" in decisions


def test_complete_workflow_readme_links_exist() -> None:
    readme = Path("examples/complete_workflow/README.md")
    payload = readme.read_text(encoding="utf-8")
    assert "../../docs/QUICK_START.md" in payload
    assert "../../docs/ARCHITECTURE_ANALYSIS.md" in payload
