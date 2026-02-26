#!/usr/bin/env python3
"""Evaluate gateway rollout gates from a metrics JSON snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gateway rollout gate evaluator")
    parser.add_argument(
        "--metrics-file",
        default="artifacts/gateway_metrics.json",
        help="Path to rollout metrics snapshot JSON",
    )
    parser.add_argument(
        "--allow-missing-metrics",
        action="store_true",
        help="Exit 0 when metrics snapshot is unavailable",
    )
    return parser.parse_args()


def _load_metrics(path: Path) -> dict[str, float] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _evaluate(metrics: dict[str, float]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    error_rate = float(metrics.get("error_rate_5xx", 0.0))
    latency_regression = float(metrics.get("p95_latency_regression_ratio", 0.0))
    readiness_success = float(metrics.get("readiness_success_rate", 1.0))
    missing_required = bool(metrics.get("missing_required_metrics", False))
    critical_alerts = int(metrics.get("critical_alert_count", 0))

    if error_rate > 0.02:
        failures.append(f"5xx error rate too high: {error_rate:.4f} > 0.0200")
    if latency_regression > 0.40:
        failures.append(f"P95 latency regression too high: {latency_regression:.4f} > 0.4000")
    if readiness_success < 0.995:
        failures.append(f"Readiness success too low: {readiness_success:.4f} < 0.9950")
    if missing_required:
        failures.append("Required rollout metrics are missing")
    if critical_alerts > 0:
        failures.append(f"Critical alerts present: {critical_alerts}")

    return (len(failures) == 0, failures)


def main() -> int:
    args = _parse_args()
    metrics_path = Path(args.metrics_file)
    metrics = _load_metrics(metrics_path)

    if metrics is None:
        message = f"[gateway-gate] metrics snapshot not found: {metrics_path}"
        if args.allow_missing_metrics:
            print(f"{message}; skipping gate in permissive mode.")
            return 0
        print(f"{message}; blocking rollout.")
        return 1

    passed, failures = _evaluate(metrics)
    if passed:
        print("[gateway-gate] PASS: rollout SLO gate satisfied.")
        return 0

    print("[gateway-gate] FAIL:")
    for failure in failures:
        print(f"  - {failure}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
