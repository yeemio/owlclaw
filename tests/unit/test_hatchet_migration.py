"""Unit tests for APScheduler -> Hatchet migration helpers."""

from __future__ import annotations

from pathlib import Path

from owlclaw.integrations.hatchet_migration import (
    APSchedulerJob,
    classify_job_complexity,
    load_jobs_from_mionyee_scenarios,
    render_hatchet_module,
    render_hatchet_workflow,
    select_canary_batch,
    split_jobs_by_complexity,
    write_complexity_modules,
    write_generated_hatchet_module,
)


def test_classify_job_complexity_variants() -> None:
    simple = APSchedulerJob(name="a", cron="0 9 * * 1-5", func_ref="x")
    stateful = APSchedulerJob(name="b", cron="0 10 * * 1-5", func_ref="x", stateful=True)
    chained = APSchedulerJob(name="c", cron="0 11 * * 1-5", func_ref="x", depends_on=["a"])

    assert classify_job_complexity(simple) == "simple_cron"
    assert classify_job_complexity(stateful) == "stateful_cron"
    assert classify_job_complexity(chained) == "chained"


def test_select_canary_batch_prefers_simple_jobs() -> None:
    jobs = [
        APSchedulerJob(name="stateful-x", cron="0 9 * * 1-5", func_ref="x", stateful=True),
        APSchedulerJob(name="simple-b", cron="0 9 * * 1-5", func_ref="x"),
        APSchedulerJob(name="simple-a", cron="0 9 * * 1-5", func_ref="x"),
        APSchedulerJob(name="chained-y", cron="0 9 * * 1-5", func_ref="x", depends_on=["simple-a"]),
    ]

    batch = select_canary_batch(jobs, max_jobs=5)
    assert [job.name for job in batch] == ["simple-a", "simple-b"]


def test_render_hatchet_workflow_contains_cron_and_source() -> None:
    job = APSchedulerJob(
        name="mionyee task 1",
        cron="30 9 * * 1-5",
        func_ref="mionyee.scheduler.entry_monitor",
    )
    rendered = render_hatchet_workflow(job)
    assert "@hatchet.task" in rendered
    assert "30 9 * * 1-5" in rendered
    assert "mionyee.scheduler.entry_monitor" in rendered


def test_load_jobs_from_mionyee_scenarios_and_render_module(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios.json"
    scenarios.write_text(
        """
[
  {
    "scenario_id": "mionyee-task-1",
    "name": "mionyee task 1",
    "input_data": {"action": "entry_check", "symbol": "AAPL"}
  },
  {
    "scenario_id": "mionyee-task-2",
    "name": "mionyee task 2",
    "input_data": {"action": "risk_review", "symbol": "MSFT"}
  }
]
""".strip(),
        encoding="utf-8",
    )
    jobs = load_jobs_from_mionyee_scenarios(scenarios)
    assert len(jobs) == 2
    assert jobs[0].cron == "30 9 * * 1-5"
    assert jobs[1].stateful is True

    module_text = render_hatchet_module(jobs)
    assert module_text.count("@hatchet.task") == 2
    output = write_generated_hatchet_module(jobs, tmp_path / "generated.py")
    assert output.exists()
    assert "@hatchet.task" in output.read_text(encoding="utf-8")


def test_split_jobs_by_complexity_and_write_modules(tmp_path: Path) -> None:
    jobs = [
        APSchedulerJob(name="simple", cron="0 9 * * 1-5", func_ref="x"),
        APSchedulerJob(name="stateful", cron="0 10 * * 1-5", func_ref="x", stateful=True),
        APSchedulerJob(name="chained", cron="0 11 * * 1-5", func_ref="x", depends_on=["simple"]),
    ]
    buckets = split_jobs_by_complexity(jobs)
    assert len(buckets["simple_cron"]) == 1
    assert len(buckets["stateful_cron"]) == 1
    assert len(buckets["chained"]) == 1

    outputs = write_complexity_modules(jobs, tmp_path)
    assert outputs["simple_cron"].exists()
    assert outputs["stateful_cron"].exists()
    assert outputs["chained"].exists()
