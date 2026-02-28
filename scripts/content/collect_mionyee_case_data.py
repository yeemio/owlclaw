"""Build Mionyee case-study comparisons from real CSV exports.

This script does not generate synthetic values. It only aggregates provided
source files and emits a report with source hashes for traceability.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LLMMetrics:
    cost_usd: float
    calls_total: int
    calls_blocked: int


@dataclass(frozen=True)
class SchedulerMetrics:
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    avg_recovery_seconds: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pct_delta(before: float, after: float) -> str:
    if before == 0:
        return "n/a"
    return f"{((after - before) / before) * 100:.2f}%"


def _safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return num / den


def load_llm_metrics(path: Path) -> LLMMetrics:
    cost_usd = 0.0
    calls_total = 0
    calls_blocked = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"cost_usd", "calls_total", "calls_blocked"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        for row in reader:
            cost_usd += float(row["cost_usd"])
            calls_total += int(row["calls_total"])
            calls_blocked += int(row["calls_blocked"])
    return LLMMetrics(cost_usd=cost_usd, calls_total=calls_total, calls_blocked=calls_blocked)


def load_scheduler_metrics(path: Path) -> SchedulerMetrics:
    total_tasks = 0
    success_tasks = 0
    failed_tasks = 0
    recovery_sum = 0.0
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"total_tasks", "success_tasks", "failed_tasks", "recovery_seconds"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        for row in reader:
            rows += 1
            total_tasks += int(row["total_tasks"])
            success_tasks += int(row["success_tasks"])
            failed_tasks += int(row["failed_tasks"])
            recovery_sum += float(row["recovery_seconds"])
    avg_recovery = _safe_div(recovery_sum, float(rows))
    return SchedulerMetrics(
        total_tasks=total_tasks,
        success_tasks=success_tasks,
        failed_tasks=failed_tasks,
        avg_recovery_seconds=avg_recovery,
    )


def build_report(
    *,
    llm_before: LLMMetrics,
    llm_after: LLMMetrics,
    scheduler_before: SchedulerMetrics,
    scheduler_after: SchedulerMetrics,
    source_hashes: dict[str, str],
) -> dict[str, object]:
    before_success_rate = _safe_div(scheduler_before.success_tasks, scheduler_before.total_tasks)
    after_success_rate = _safe_div(scheduler_after.success_tasks, scheduler_after.total_tasks)
    before_block_ratio = _safe_div(llm_before.calls_blocked, llm_before.calls_total)
    after_block_ratio = _safe_div(llm_after.calls_blocked, llm_after.calls_total)

    return {
        "source_hashes": source_hashes,
        "llm": {
            "before": llm_before.__dict__,
            "after": llm_after.__dict__,
            "delta_cost_pct": _pct_delta(llm_before.cost_usd, llm_after.cost_usd),
            "delta_calls_pct": _pct_delta(float(llm_before.calls_total), float(llm_after.calls_total)),
            "before_block_ratio": round(before_block_ratio, 4),
            "after_block_ratio": round(after_block_ratio, 4),
        },
        "scheduler": {
            "before": scheduler_before.__dict__,
            "after": scheduler_after.__dict__,
            "delta_success_rate_pct": _pct_delta(before_success_rate, after_success_rate),
            "delta_recovery_seconds_pct": _pct_delta(
                scheduler_before.avg_recovery_seconds,
                scheduler_after.avg_recovery_seconds,
            ),
        },
        "authenticity": {
            "rule": "All metrics are aggregated from provided raw CSV exports only.",
            "fabrication_allowed": False,
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    llm = report["llm"]
    scheduler = report["scheduler"]
    source_hashes = report["source_hashes"]
    assert isinstance(llm, dict)
    assert isinstance(scheduler, dict)
    assert isinstance(source_hashes, dict)
    llm_before = llm["before"]
    llm_after = llm["after"]
    scheduler_before = scheduler["before"]
    scheduler_after = scheduler["after"]
    assert isinstance(llm_before, dict) and isinstance(llm_after, dict)
    assert isinstance(scheduler_before, dict) and isinstance(scheduler_after, dict)

    lines = [
        "# Mionyee Case Data Comparison",
        "",
        "## Source Integrity",
        "",
    ]
    for name, digest in source_hashes.items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend(
        [
            "",
            "## LLM Governance Comparison",
            "",
            "| Metric | Before | After | Delta |",
            "|---|---:|---:|---:|",
            f"| Cost (USD) | {llm_before['cost_usd']:.4f} | {llm_after['cost_usd']:.4f} | {llm['delta_cost_pct']} |",
            f"| Total Calls | {llm_before['calls_total']} | {llm_after['calls_total']} | {llm['delta_calls_pct']} |",
            f"| Block Ratio | {llm['before_block_ratio']:.4f} | {llm['after_block_ratio']:.4f} | n/a |",
            "",
            "## Scheduler Migration Comparison",
            "",
            "| Metric | Before | After | Delta |",
            "|---|---:|---:|---:|",
            f"| Success Rate | {_safe_div(scheduler_before['success_tasks'], scheduler_before['total_tasks']):.4f} | "
            f"{_safe_div(scheduler_after['success_tasks'], scheduler_after['total_tasks']):.4f} | "
            f"{scheduler['delta_success_rate_pct']} |",
            f"| Avg Recovery Seconds | {scheduler_before['avg_recovery_seconds']:.4f} | "
            f"{scheduler_after['avg_recovery_seconds']:.4f} | {scheduler['delta_recovery_seconds_pct']} |",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Mionyee real metrics into case-study report.")
    parser.add_argument("--llm-before", required=True)
    parser.add_argument("--llm-after", required=True)
    parser.add_argument("--scheduler-before", required=True)
    parser.add_argument("--scheduler-after", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    llm_before_path = Path(args.llm_before)
    llm_after_path = Path(args.llm_after)
    scheduler_before_path = Path(args.scheduler_before)
    scheduler_after_path = Path(args.scheduler_after)

    llm_before = load_llm_metrics(llm_before_path)
    llm_after = load_llm_metrics(llm_after_path)
    scheduler_before = load_scheduler_metrics(scheduler_before_path)
    scheduler_after = load_scheduler_metrics(scheduler_after_path)

    source_hashes = {
        llm_before_path.name: _sha256(llm_before_path),
        llm_after_path.name: _sha256(llm_after_path),
        scheduler_before_path.name: _sha256(scheduler_before_path),
        scheduler_after_path.name: _sha256(scheduler_after_path),
    }
    report = build_report(
        llm_before=llm_before,
        llm_after=llm_after,
        scheduler_before=scheduler_before,
        scheduler_after=scheduler_after,
        source_hashes=source_hashes,
    )

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"[mionyee-data] wrote {output_json}")
    print(f"[mionyee-data] wrote {output_md}")


if __name__ == "__main__":
    main()
