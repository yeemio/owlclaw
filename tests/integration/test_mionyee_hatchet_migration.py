"""Integration checks for mionyee APScheduler -> Hatchet migration replay."""

from __future__ import annotations

from pathlib import Path

from owlclaw.integrations.hatchet_migration import (
    dual_run_replay_compare,
    load_jobs_from_mionyee_scenarios,
    select_canary_batch,
)


def test_dual_run_replay_all_jobs_match() -> None:
    jobs = load_jobs_from_mionyee_scenarios("config/e2e/scenarios/mionyee-tasks.json")
    report = dual_run_replay_compare(jobs)
    assert report["compared"] >= 1
    assert report["matched"] == report["compared"]
    assert report["mismatches"] == []


def test_dual_run_replay_canary_batch_is_non_empty() -> None:
    jobs = load_jobs_from_mionyee_scenarios("config/e2e/scenarios/mionyee-tasks.json")
    canary = select_canary_batch(jobs)
    assert canary
    report = dual_run_replay_compare(canary)
    assert report["matched"] == report["compared"] == len(canary)


def test_generated_hatchet_files_exist_for_first_batch() -> None:
    generated = Path("examples/mionyee-trading/generated_hatchet_tasks.py")
    generated_canary = Path("examples/mionyee-trading/generated_hatchet_tasks_canary.py")
    assert generated.exists()
    assert generated_canary.exists()
