"""Tests for Mionyee input validation script."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_verify_mionyee_inputs_pass(tmp_path: Path) -> None:
    _write(tmp_path / "llm_before.csv", "cost_usd,calls_total,calls_blocked\n1.0,10,1\n")
    _write(tmp_path / "llm_after.csv", "cost_usd,calls_total,calls_blocked\n0.8,9,2\n")
    _write(tmp_path / "scheduler_before.csv", "total_tasks,success_tasks,failed_tasks,recovery_seconds\n10,9,1,20\n")
    _write(tmp_path / "scheduler_after.csv", "total_tasks,success_tasks,failed_tasks,recovery_seconds\n10,10,0,8\n")

    output = tmp_path / "validation.json"
    cmd = [
        "poetry",
        "run",
        "python",
        "scripts/content/verify_mionyee_case_inputs.py",
        "--input-dir",
        str(tmp_path),
        "--output",
        str(output),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[2])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert all(item["status"] == "ok" for item in payload["results"])


def test_verify_mionyee_inputs_fail_for_missing_and_empty(tmp_path: Path) -> None:
    _write(tmp_path / "llm_before.csv", "cost_usd,calls_total,calls_blocked\n")
    _write(tmp_path / "scheduler_before.csv", "total_tasks,success_tasks,failed_tasks,recovery_seconds\n1,1,0,1\n")

    output = tmp_path / "validation.json"
    cmd = [
        "poetry",
        "run",
        "python",
        "scripts/content/verify_mionyee_case_inputs.py",
        "--input-dir",
        str(tmp_path),
        "--output",
        str(output),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[2])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    statuses = {item["file_name"]: item["status"] for item in payload["results"]}
    assert statuses["llm_before.csv"] == "empty"
    assert statuses["llm_after.csv"] == "missing"
    assert statuses["scheduler_after.csv"] == "missing"

