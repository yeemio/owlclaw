"""Unit tests for mionyee migration acceptance helpers."""

from __future__ import annotations

import json
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from owlclaw.integrations.hatchet_acceptance import (
    build_status_snapshot,
    evaluate_e2e_acceptance,
    verify_restart_recovery,
)
from owlclaw.integrations.hatchet_migration import APSchedulerJob


def test_verify_restart_recovery_matches_before_after() -> None:
    before = [APSchedulerJob(name="a", cron="0 9 * * 1-5", func_ref="x")]
    after = [APSchedulerJob(name="a", cron="0 9 * * 1-5", func_ref="x")]
    result = verify_restart_recovery(before, after)
    assert result["recovered"] is True
    assert result["recovered_count"] == 1


def test_build_status_snapshot_reads_report_and_config(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps({"compared": 2, "matched": 2, "match_rate": 1.0, "mismatches": []}),
        encoding="utf-8",
    )
    config = tmp_path / "owlclaw.yaml"
    config.write_text(
        yaml.safe_dump({"migration": {"scheduler_backend": "hatchet"}}, sort_keys=False),
        encoding="utf-8",
    )
    snapshot = build_status_snapshot(report, config)
    assert snapshot["backend"] == "hatchet"
    assert snapshot["match_rate"] == 1.0


def test_evaluate_e2e_acceptance_requires_all_checks() -> None:
    ok = evaluate_e2e_acceptance(
        recovery_ok=True,
        status_snapshot={"backend": "hatchet", "compared": 1, "match_rate": 1.0, "mismatch_count": 0},
        rollback_verified=True,
        generated_files_ok=True,
    )
    assert ok["passed"] is True

    bad = evaluate_e2e_acceptance(
        recovery_ok=True,
        status_snapshot={"backend": "hatchet", "compared": 1, "match_rate": 0.5, "mismatch_count": 1},
        rollback_verified=True,
        generated_files_ok=True,
    )
    assert bad["passed"] is False
