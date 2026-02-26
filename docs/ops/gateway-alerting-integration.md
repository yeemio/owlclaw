# Gateway Alerting Integration

Last updated: 2026-02-26

## Scope

This document maps gateway rollout metrics to dashboard panels and alert rules.

## Dashboard Panels

1. `gateway.error_rate_5xx`
2. `gateway.p95_latency_regression_ratio`
3. `gateway.readiness_success_rate`
4. `gateway.critical_alert_count`

## Alert Rules

1. Critical: `error_rate_5xx > 0.02` for 3 minutes
2. Critical: `p95_latency_regression_ratio > 0.40` for 5 minutes
3. Warning: `readiness_success_rate < 0.997` for 5 minutes
4. Warning: missing metrics snapshot for current rollout stage

## Pipeline Integration

1. Gate step calls `scripts/ops/gateway_gate_check.py`.
2. Failure path calls `scripts/ops/gateway_rollback_executor.py --dry-run` (or production mode in rollout env).
3. Gate output and alert snapshots are archived in the workflow artifacts.

## Evidence

Each rollout stage must keep:

1. Gate check console output
2. Dashboard snapshot link
3. Active alert list
4. Pipeline run ID and commit SHA
