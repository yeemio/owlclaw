"""Report generation for e2e validation and comparison outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from owlclaw.e2e.models import ExecutionResult


class ReportGenerator:
    """Generate and export validation/comparison/performance reports."""

    def generate_validation_report(self, results: list[ExecutionResult]) -> dict[str, Any]:
        """Generate one consolidated validation report for execution results."""
        total_tests = len(results)
        passed_tests = sum(1 for result in results if result.status.value == "passed")
        failed_tests = sum(1 for result in results if result.status.value in {"failed", "error"})
        skipped_tests = sum(1 for result in results if result.status.value == "skipped")
        total_duration = sum(result.duration_ms for result in results)
        success_rate = (float(passed_tests) / total_tests) if total_tests > 0 else 0.0

        failures: list[dict[str, Any]] = []
        for result in results:
            if result.status.value in {"failed", "error"}:
                failures.append(
                    {
                        "scenario_id": result.scenario_id,
                        "status": result.status.value,
                        "errors": list(result.errors),
                        "debug_info": {
                            "event_count": len(result.events),
                            "trace_count": len(result.metadata.get("traces", [])),
                            "metadata": result.metadata,
                        },
                    }
                )

        sections = [
            {
                "title": "execution_overview",
                "content": "Per-scenario execution details",
                "data": [self._serialize_execution_result(result) for result in results],
                "charts": [],
            },
            {
                "title": "failures",
                "content": "Failure stack and debug information",
                "data": failures,
                "charts": [],
            },
        ]
        report = {
            "id": f"validation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "title": "E2E Validation Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "test_coverage": self._calculate_coverage(results),
                "success_rate": success_rate,
                "average_response_time": (total_duration / total_tests) if total_tests > 0 else 0.0,
                "critical_issues": failed_tests,
            },
            "sections": sections,
            "charts": [
                {
                    "type": "bar",
                    "title": "Execution Status Distribution",
                    "data": {
                        "labels": ["passed", "failed", "skipped"],
                        "values": [passed_tests, failed_tests, skipped_tests],
                    },
                    "options": {"stacked": False},
                }
            ],
            "recommendations": self._build_recommendations(failed_tests=failed_tests, success_rate=success_rate),
        }
        return report

    def generate_comparison_report(self, comparison: dict[str, Any]) -> dict[str, Any]:
        """Generate comparison report with visualization-ready chart payloads."""
        quality_diff = comparison.get("decision_quality_diff", {})
        performance_diff = comparison.get("performance_diff", {})
        anomalies = comparison.get("anomalies", [])
        report = {
            "id": f"comparison-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "title": "E2E Decision Comparison Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "scenario_id": comparison.get("scenario_id", "unknown"),
                "anomaly_count": len(anomalies) if isinstance(anomalies, list) else 0,
                "quality_metrics": list(quality_diff.keys()) if isinstance(quality_diff, dict) else [],
                "performance_metrics": list(performance_diff.keys()) if isinstance(performance_diff, dict) else [],
            },
            "sections": [
                {
                    "title": "quality_diff",
                    "content": "Decision quality metric deltas between V3 Agent and Original Cron.",
                    "data": quality_diff,
                    "charts": ["quality_delta_chart"],
                },
                {
                    "title": "performance_diff",
                    "content": "Performance metric deltas between V3 Agent and Original Cron.",
                    "data": performance_diff,
                    "charts": ["performance_delta_chart"],
                },
                {
                    "title": "anomalies",
                    "content": "Detected anomalies above threshold.",
                    "data": anomalies,
                    "charts": [],
                },
            ],
            "charts": [
                {
                    "id": "quality_delta_chart",
                    "type": "bar",
                    "title": "Decision Quality Delta",
                    "data": {
                        "labels": list(quality_diff.keys()) if isinstance(quality_diff, dict) else [],
                        "values": list(quality_diff.values()) if isinstance(quality_diff, dict) else [],
                    },
                    "options": {"show_legend": True},
                },
                {
                    "id": "performance_delta_chart",
                    "type": "line",
                    "title": "Performance Delta",
                    "data": {
                        "labels": list(performance_diff.keys()) if isinstance(performance_diff, dict) else [],
                        "values": list(performance_diff.values()) if isinstance(performance_diff, dict) else [],
                    },
                    "options": {"smooth": True},
                },
            ],
            "recommendations": ["Review anomaly details before increasing migration_weight."]
            if anomalies
            else ["No blocking anomalies detected."],
        }
        return report

    def generate_performance_report(self, metrics: list[dict[str, float]]) -> dict[str, Any]:
        """Generate performance report with trend visualization data."""
        response_times = [float(item.get("response_time", 0.0)) for item in metrics]
        throughputs = [float(item.get("throughput", 0.0)) for item in metrics]
        report = {
            "id": f"performance-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "title": "E2E Performance Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "samples": len(metrics),
                "avg_response_time": (sum(response_times) / len(response_times)) if response_times else 0.0,
                "avg_throughput": (sum(throughputs) / len(throughputs)) if throughputs else 0.0,
            },
            "sections": [
                {
                    "title": "performance_trend",
                    "content": "Historical performance trend.",
                    "data": metrics,
                    "charts": ["performance_trend_chart"],
                }
            ],
            "charts": [
                {
                    "id": "performance_trend_chart",
                    "type": "line",
                    "title": "Response Time Trend",
                    "data": {
                        "labels": [str(index) for index in range(len(response_times))],
                        "values": response_times,
                    },
                    "options": {"y_axis": "ms"},
                }
            ],
            "recommendations": [],
        }
        return report

    def export_report(self, report: dict[str, Any], format_name: str) -> str:
        """Export report into JSON, HTML, or PDF textual payload."""
        normalized = format_name.strip().lower()
        if normalized == "json":
            return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        if normalized == "html":
            return self._to_html(report)
        if normalized == "pdf":
            return self._to_pdf(report)
        raise ValueError(f"unsupported report format: {format_name}")

    def _serialize_execution_result(self, result: ExecutionResult) -> dict[str, Any]:
        return {
            "scenario_id": result.scenario_id,
            "execution_time_ms": result.duration_ms,
            "status": result.status.value,
            "result": result.metadata.get("output", {}),
            "started_at": result.started_at.isoformat(),
            "ended_at": result.ended_at.isoformat(),
            "errors": list(result.errors),
        }

    def _calculate_coverage(self, results: list[ExecutionResult]) -> float:
        if not results:
            return 0.0
        traced = sum(1 for result in results if len(result.metadata.get("traces", [])) > 0)
        return float(traced) / float(len(results))

    def _build_recommendations(self, *, failed_tests: int, success_rate: float) -> list[str]:
        recommendations: list[str] = []
        if failed_tests > 0:
            recommendations.append("Investigate failed scenarios before release.")
        if success_rate < 0.9:
            recommendations.append("Increase validation coverage and rerun critical scenarios.")
        if not recommendations:
            recommendations.append("Validation quality is acceptable for next phase.")
        return recommendations

    def _to_html(self, report: dict[str, Any]) -> str:
        title = str(report.get("title", "E2E Report"))
        summary = report.get("summary", {})
        sections = report.get("sections", [])
        return (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'><title>"
            + title
            + "</title></head><body><h1>"
            + title
            + "</h1><h2>Summary</h2><pre>"
            + json.dumps(summary, ensure_ascii=False, indent=2)
            + "</pre><h2>Sections</h2><pre>"
            + json.dumps(sections, ensure_ascii=False, indent=2)
            + "</pre></body></html>"
        )

    def _to_pdf(self, report: dict[str, Any]) -> str:
        title = str(report.get("title", "E2E Report"))
        summary_text = json.dumps(report.get("summary", {}), ensure_ascii=True)
        body = f"{title} | {summary_text}"[:120]
        pdf = (
            "%PDF-1.4\n"
            "1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            "2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources<<>> >>endobj\n"
            f"4 0 obj<< /Length {len(body) + 30} >>stream\nBT /F1 10 Tf 10 100 Td ({body}) Tj ET\nendstream endobj\n"
            "xref\n0 5\n0000000000 65535 f \n"
            "0000000010 00000 n \n0000000060 00000 n \n0000000118 00000 n \n0000000240 00000 n \n"
            "trailer<< /Size 5 /Root 1 0 R >>\nstartxref\n360\n%%EOF"
        )
        return pdf
