"""Unit and property tests for e2e report generation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.comparison_engine import ComparisonEngine
from owlclaw.e2e.models import ExecutionResult, ExecutionStatus
from owlclaw.e2e.replay import ReplayResult
from owlclaw.e2e.report_generator import ReportGenerator


def _result(
    *,
    scenario_id: str,
    status: ExecutionStatus,
    duration_ms: float = 10.0,
    errors: list[str] | None = None,
) -> ExecutionResult:
    now = datetime.now(UTC)
    return ExecutionResult(
        scenario_id=scenario_id,
        status=status,
        started_at=now,
        ended_at=now + timedelta(milliseconds=duration_ms),
        duration_ms=duration_ms,
        events=[],
        metrics={"throughput": 1.0},
        errors=errors or [],
        metadata={"output": {"ok": status.value == "passed"}, "traces": [{"phase": "done"}], "resource_usage": {}},
    )


def test_export_report_supports_json_html_pdf() -> None:
    generator = ReportGenerator()
    report = generator.generate_validation_report([_result(scenario_id="s", status=ExecutionStatus.PASSED)])

    exported_json = generator.export_report(report, "json")
    exported_html = generator.export_report(report, "html")
    exported_pdf = generator.export_report(report, "pdf")

    assert exported_json.strip().startswith("{")
    assert exported_html.lower().startswith("<!doctype html>")
    assert exported_pdf.startswith("%PDF-1.4")


class TestReportGeneratorProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        status=st.sampled_from(
            [ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.ERROR, ExecutionStatus.SKIPPED]
        ),
        duration=st.floats(min_value=0.0, max_value=20000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_validation_report_contains_execution_time_status_result(
        self,
        status: ExecutionStatus,
        duration: float,
    ) -> None:
        """Property 3: report contains execution time, status, and result fields."""
        generator = ReportGenerator()
        report = generator.generate_validation_report([_result(scenario_id="a", status=status, duration_ms=duration)])

        details = report["sections"][0]["data"][0]
        assert "execution_time_ms" in details
        assert "status" in details
        assert "result" in details

    @settings(max_examples=100, deadline=None)
    @given(
        count=st.integers(min_value=1, max_value=30),
        failed=st.integers(min_value=0, max_value=30),
    )
    def test_property_validation_report_summary_is_complete(self, count: int, failed: int) -> None:
        """Property 16: report summary includes coverage/success/failure/performance fields."""
        failed_count = min(failed, count)
        generator = ReportGenerator()
        results = [
            _result(scenario_id=f"s-{index}", status=ExecutionStatus.FAILED if index < failed_count else ExecutionStatus.PASSED)
            for index in range(count)
        ]
        report = generator.generate_validation_report(results)
        summary = report["summary"]
        required = {
            "total_tests",
            "passed_tests",
            "failed_tests",
            "skipped_tests",
            "test_coverage",
            "success_rate",
            "average_response_time",
        }
        assert required.issubset(summary.keys())

    @settings(max_examples=100, deadline=None)
    @given(
        v3_duration=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        cron_duration=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_comparison_report_contains_visualization_and_statistics(
        self,
        v3_duration: float,
        cron_duration: float,
    ) -> None:
        """Property 7 + 17: comparison report includes charts and statistics."""
        comparison_engine = ComparisonEngine()
        comparison = comparison_engine.compare(
            _result(scenario_id="cmp", status=ExecutionStatus.PASSED, duration_ms=v3_duration),
            _result(scenario_id="cmp", status=ExecutionStatus.PASSED, duration_ms=cron_duration),
        )
        report = ReportGenerator().generate_comparison_report(comparison)

        assert "summary" in report
        assert "anomaly_count" in report["summary"]
        assert isinstance(report["charts"], list)
        assert len(report["charts"]) >= 1

    @settings(max_examples=100, deadline=None)
    @given(format_name=st.sampled_from(["json", "html", "pdf"]))
    def test_property_report_export_works_for_all_formats(self, format_name: str) -> None:
        """Property 18: all required export formats can be produced."""
        generator = ReportGenerator()
        report = generator.generate_validation_report([_result(scenario_id="e", status=ExecutionStatus.PASSED)])
        exported = generator.export_report(report, format_name)
        assert isinstance(exported, str)
        assert len(exported) > 0

    @settings(max_examples=100, deadline=None)
    @given(error_text=st.text(min_size=1, max_size=200))
    def test_property_failure_report_contains_error_stack_and_debug_info(self, error_text: str) -> None:
        """Property 19: failures include error stack and debug metadata."""
        generator = ReportGenerator()
        failed_result = _result(
            scenario_id="f-1",
            status=ExecutionStatus.ERROR,
            errors=[error_text],
        )
        report = generator.generate_validation_report([failed_result])

        failures_section = next(section for section in report["sections"] if section["title"] == "failures")
        assert len(failures_section["data"]) == 1
        failure_item = failures_section["data"][0]
        assert "errors" in failure_item
        assert failure_item["errors"][0] == error_text
        assert "debug_info" in failure_item
        assert "metadata" in failure_item["debug_info"]


def test_export_report_rejects_unknown_format() -> None:
    generator = ReportGenerator()
    report = generator.generate_validation_report([_result(scenario_id="x", status=ExecutionStatus.PASSED)])
    with pytest.raises(ValueError):
        generator.export_report(report, "xml")


def test_generate_replay_report_contains_visualized_metrics() -> None:
    replay_result = ReplayResult(
        total_events=3,
        agent_decisions=[{"decision": "a"}],
        cron_decisions=[{"decision": "a"}],
        consistency_rate=0.9,
        deviation_distribution={"low": 2, "medium": 1, "high": 0, "critical": 0},
        quality_trend=[1.0, 1.0, 0.9],
        memory_growth=[1, 2, 3],
    )
    report = ReportGenerator().generate_replay_report(replay_result)
    assert report["summary"]["total_events"] == 3
    assert report["summary"]["consistency_rate"] == 0.9
    assert len(report["charts"]) == 2
