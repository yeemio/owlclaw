"""Tests for scripts/release_oidc_preflight.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_release_oidc_preflight_ready_with_local_inputs(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "release_oidc_preflight.py"

    branch = tmp_path / "branch.json"
    rulesets = tmp_path / "rulesets.json"
    log_file = tmp_path / "run.log"
    output_rel = Path(".tmp") / "test_release_oidc_preflight_ready.md"
    report = repo / output_rel
    report.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        branch,
        {
            "required_status_checks": {
                "strict": True,
                "contexts": ["Lint", "Test", "Build"],
            }
        },
    )
    _write_json(
        rulesets,
        [
            {
                "name": "release-branch-protection",
                "target": "branch",
                "enforcement": "active",
            }
        ],
    )
    log_file.write_text("Publish to TestPyPI\nsuccess", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--branch-protection-json",
            str(branch),
            "--rulesets-json",
            str(rulesets),
            "--run-log",
            str(log_file),
            "--output",
            str(output_rel),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = report.read_text(encoding="utf-8")
    assert "status: READY" in payload
    report.unlink(missing_ok=True)


def test_release_oidc_preflight_detects_trusted_publisher_blocker(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "release_oidc_preflight.py"

    branch = tmp_path / "branch.json"
    rulesets = tmp_path / "rulesets.json"
    log_file = tmp_path / "run.log"
    output_rel = Path(".tmp") / "test_release_oidc_preflight_blocked.md"
    report = repo / output_rel
    report.parent.mkdir(parents=True, exist_ok=True)

    _write_json(
        branch,
        {
            "required_status_checks": {
                "strict": True,
                "contexts": ["Lint", "Test", "Build"],
            }
        },
    )
    _write_json(
        rulesets,
        [
            {
                "name": "release-branch-protection",
                "target": "branch",
                "enforcement": "active",
            }
        ],
    )
    log_file.write_text(
        "Publish to TestPyPI\nHTTPError: 403 Forbidden from https://test.pypi.org/legacy/",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--branch-protection-json",
            str(branch),
            "--rulesets-json",
            str(rulesets),
            "--run-log",
            str(log_file),
            "--output",
            str(output_rel),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 3, result.stderr
    payload = report.read_text(encoding="utf-8")
    assert "status: BLOCKED" in payload
    assert "Trusted Publisher" in payload
    report.unlink(missing_ok=True)
