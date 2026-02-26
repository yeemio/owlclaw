#!/usr/bin/env python3
"""Run gateway drill scenarios against metric snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gateway drill runner")
    parser.add_argument("--scenario", choices=["canary-fail", "full-success"], required=True)
    parser.add_argument("--metrics-file", required=True)
    return parser.parse_args()


def _evaluate(metrics: dict[str, float]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if float(metrics.get("error_rate_5xx", 0.0)) > 0.02:
        issues.append("error_rate_5xx > 2%")
    if float(metrics.get("p95_latency_regression_ratio", 0.0)) > 0.40:
        issues.append("p95_latency_regression_ratio > 40%")
    if float(metrics.get("readiness_success_rate", 1.0)) < 0.995:
        issues.append("readiness_success_rate < 99.5%")
    if int(metrics.get("critical_alert_count", 0)) > 0:
        issues.append("critical_alert_count > 0")
    if bool(metrics.get("missing_required_metrics", False)):
        issues.append("missing_required_metrics=true")
    return (len(issues) == 0, issues)


def main() -> int:
    args = _parse_args()
    metrics_path = Path(args.metrics_file)
    with metrics_path.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)

    passed, issues = _evaluate(metrics)
    print(f"[gateway-drill] scenario={args.scenario}")
    if passed:
        print("[gateway-drill] decision=promote")
        return 0

    print("[gateway-drill] decision=rollback")
    for issue in issues:
        print(f"  - {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
