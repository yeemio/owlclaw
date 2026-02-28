"""Tests for content-launch readiness assessment script."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.content.assess_content_launch_readiness import assess


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_readiness_reports_missing_external_inputs(tmp_path: Path) -> None:
    report = assess(
        case_data_json=tmp_path / "missing-case.json",
        case_data_md=tmp_path / "missing-case.md",
        direction_json=tmp_path / "missing-direction.json",
        publication_json=tmp_path / "missing-publication.json",
        case_study_md=tmp_path / "case-study.md",
    )
    assert report["all_external_gates_passed"] is False
    assert "task_1_data_collected" in report["remaining_tasks"]
    assert "task_2_1_direction_selected" in report["remaining_tasks"]
    assert "task_2_6_2_7_5_1_published" in report["remaining_tasks"]


def test_readiness_passes_when_all_evidence_present(tmp_path: Path) -> None:
    case_data_json = tmp_path / "mionyee-case-data.json"
    case_data_md = tmp_path / "mionyee-case-data.md"
    direction_json = tmp_path / "article-direction-decision.json"
    publication_json = tmp_path / "publication-evidence.json"
    case_study_md = tmp_path / "mionyee-case-study.md"

    _write_json(case_data_json, {"llm": {}, "scheduler": {}})
    case_data_md.write_text("# data\n", encoding="utf-8")
    _write_json(direction_json, {"direction": "A"})
    _write_json(publication_json, {"all_required_passed": True})
    case_study_md.write_text("# case study\n", encoding="utf-8")

    report = assess(
        case_data_json=case_data_json,
        case_data_md=case_data_md,
        direction_json=direction_json,
        publication_json=publication_json,
        case_study_md=case_study_md,
    )
    assert report["all_external_gates_passed"] is True
    assert report["remaining_tasks"] == []
