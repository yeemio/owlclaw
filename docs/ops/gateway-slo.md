# Gateway SLO

Last updated: 2026-02-26

## Objectives

This SLO set is used by rollout gates and rollback logic for protocol-facing runtime.

## Service Level Objectives

1. Availability (gateway request success): >= 99.9%
2. 5xx error rate during rollout stages: <= 2.0%
3. P95 latency regression versus baseline: <= 40%
4. Readiness probe success rate: >= 99.5%

## Error Budget

1. Monthly availability budget: 0.1%
2. Rollout budget guardrail: if 50% of monthly budget is consumed, force manual approvals only.

## Alerts

1. Critical: 5xx error rate > 2.0% for 3 minutes
2. Critical: P95 latency regression > 40% for 5 minutes
3. Warning: readiness probe success < 99.7% for 5 minutes
4. Warning: missing required metrics for 2 minutes

## Gate Mapping

1. Canary gate: all critical alerts must be absent
2. Expansion gate: no critical alerts and no active warning alerts
3. Full gate: same as expansion plus manual approval record

## Acceptance Matrix

| Scenario | Check | Evidence | Pass |
|---|---|---|---|
| Canary rollout | Gate decision follows SLO rules | Pipeline logs | [ ] |
| Canary failure | Auto rollback triggered | Rollback logs | [ ] |
| Full rollout | Metrics remain stable | Dashboard snapshot | [ ] |
| Manual rollback | Runbook executed end-to-end | Drill record | [ ] |
