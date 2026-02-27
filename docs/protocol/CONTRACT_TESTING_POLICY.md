# Contract Testing Policy

> Scope: runtime thresholds, artifact binding, and incident handling for contract-testing.
> Last Updated: 2026-02-26

## 1. Runtime Thresholds

- PR minimal contract suite target: `<= 8 minutes`.
- Nightly full contract regression target: `<= 45 minutes`.
- Hard timeout suggestion per single gate run: `<= 90 seconds`.

## 2. Acceptance Matrix (Artifact-bound)

| Scenario | Expected | Artifact |
|---|---|---|
| OpenAPI additive change | gate pass | contract-gate workflow log |
| OpenAPI breaking change | gate block | contract diff report JSON |
| MCP core-path regression | tests pass | pytest output artifact |
| Drill execution | block + report generated | `docs/protocol/reports/contract-testing-drill-latest.md` |

Template:

- `docs/protocol/templates/CONTRACT_DIFF_REPORT_TEMPLATE.md`

## 3. T+0 ~ T+15 Playbook

- `T+0`: block merge queue and flag contract gate incident.
- `T+3`: export diff report and failed replay sample.
- `T+6`: identify rule bug vs true breaking change.
- `T+10`: patch rules/tests and rerun minimal suite.
- `T+15`: restore pipeline and publish postmortem.

