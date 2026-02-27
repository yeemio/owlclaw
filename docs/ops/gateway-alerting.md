# Gateway Alerting and Dashboard Mapping

> Scope: dashboard and alert rule linkage for rollout gates.
> Last Updated: 2026-02-26

## 1. Dashboard Panels

- request error rate (canary/expansion/full by stage)
- p95 latency trend (baseline vs active release)
- readiness/health probe status
- rollback action timeline

## 2. Alert Rules

- critical: error rate > 2% for 2 consecutive minutes
- critical: p95 latency increase > 40% for 5 minutes
- warning: missing metrics window > 2 minutes

## 3. Gate Integration

- gate evaluator reads alert state and SLO metrics before promotion
- any critical alert forces rollback path
- missing metrics blocks promotion and requires manual review

