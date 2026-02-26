# Gateway SLO

> Scope: SLO and error-budget baseline for gateway runtime operations.
> Last Updated: 2026-02-26

## 1. SLO Indicators

- availability: `>= 99.9%`
- p95 request latency: `<= 800ms` (steady-state)
- protocol error rate: `<= 2%` during rollout windows

## 2. Error Budget Policy

- monthly error budget target: `0.1%`
- budget burn warning: `>= 50%`
- promotion blocked when burn exceeds `>= 80%` in current window

## 3. Stage Gates

- canary gate: 10-minute window, all SLO checks green
- expansion gate: 15-minute window, no critical alerts
- full rollout gate: 30-minute verification window

## 4. Acceptance Matrix

| Scenario | Expected | Evidence |
|---|---|---|
| canary pass | promote to expansion | rollout logs + metrics snapshot |
| canary fail | auto rollback | rollback log |
| full rollout pass | stay at 100% | dashboard snapshot |
| manual rollback | runbook executable | incident record |

Template:

- `docs/ops/templates/GATEWAY_ACCEPTANCE_MATRIX_TEMPLATE.md`

