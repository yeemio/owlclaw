# Release Supply Chain Policy

> Scope: release supply chain gate thresholds and acceptance evidence.
> Last Updated: 2026-02-26

## 1. Quantitative Thresholds

- TestPyPI publish success rate target: `>= 99%` (last 20 runs).
- post-publish install smoke runtime target: `<= 5 minutes`.
- provenance archive completeness: `100%` for release runs.

## 2. Acceptance Matrix

| Scenario | Expected | Evidence |
|---|---|---|
| TestPyPI release | OIDC publish success | release workflow logs |
| PyPI release | package install succeeds | smoke install step log |
| provenance | attestation generated | workflow attestation record |
| rollback/retry | runbook executable | incident + rerun record |

## 3. T+0 ~ T+15 Playbook

- `T+0`: release failure detected and workflow stops.
- `T+3`: collect logs, report artifact, and failure stage.
- `T+6`: run TestPyPI replay to isolate config/packaging issue.
- `T+10`: execute retry or rollback path with approver note.
- `T+15`: publish status summary and remediation plan.

