"""Tests for Mionyee case data aggregation script."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_collect_mionyee_case_data_generates_json_and_markdown(tmp_path: Path) -> None:
    llm_before = tmp_path / "llm_before.csv"
    llm_after = tmp_path / "llm_after.csv"
    scheduler_before = tmp_path / "scheduler_before.csv"
    scheduler_after = tmp_path / "scheduler_after.csv"
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    _write(
        llm_before,
        "cost_usd,calls_total,calls_blocked\n"
        "10.5,100,10\n"
        "9.5,80,8\n",
    )
    _write(
        llm_after,
        "cost_usd,calls_total,calls_blocked\n"
        "7.0,70,12\n"
        "6.0,60,11\n",
    )
    _write(
        scheduler_before,
        "total_tasks,success_tasks,failed_tasks,recovery_seconds\n"
        "100,90,10,30\n"
        "100,92,8,28\n",
    )
    _write(
        scheduler_after,
        "total_tasks,success_tasks,failed_tasks,recovery_seconds\n"
        "100,98,2,8\n"
        "100,99,1,7\n",
    )

    cmd = [
        "poetry",
        "run",
        "python",
        "scripts/content/collect_mionyee_case_data.py",
        "--llm-before",
        str(llm_before),
        "--llm-after",
        str(llm_after),
        "--scheduler-before",
        str(scheduler_before),
        "--scheduler-after",
        str(scheduler_after),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[2])

    assert output_json.exists()
    assert output_md.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["authenticity"]["fabrication_allowed"] is False
    assert report["llm"]["before"]["cost_usd"] == 20.0
    assert report["llm"]["after"]["cost_usd"] == 13.0
    assert report["scheduler"]["before"]["total_tasks"] == 200
    assert report["scheduler"]["after"]["success_tasks"] == 197

    markdown = output_md.read_text(encoding="utf-8")
    assert "LLM Governance Comparison" in markdown
    assert "Scheduler Migration Comparison" in markdown

