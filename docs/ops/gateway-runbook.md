# Gateway Runbook

Last updated: 2026-02-26

## Preconditions

1. Release pipeline run ID is known.
2. Current stage (canary, expansion, full) is identified.
3. Oncall owner is assigned.

## Automatic Rollback Triggers

Rollback is triggered automatically when:

1. 5xx error rate > 2.0% for 3 consecutive minutes
2. P95 latency regression > 40% for 5 consecutive minutes
3. Readiness probe failures exceed 0.5% for 3 consecutive minutes

## Manual Rollback Triggers

Oncall must trigger rollback when:

1. External dependency outage causes unstable gateway behavior
2. Security or auth regression is observed
3. Metrics pipeline is degraded and risk cannot be assessed safely

## Rollback Procedure

1. Freeze promotion in the active pipeline run.
2. Execute rollback job to previous stable artifact.
3. Confirm deployment status reaches healthy state.
4. Keep traffic at pre-rollout stable version.

## Post-rollback Verification

Run all checks before declaring recovery:

1. Health and readiness probe status is green for 10 minutes
2. 5xx error rate returns to baseline threshold
3. P95 latency returns to baseline range
4. Key business probes pass (trigger, query, and auth paths)

## Incident Timeline (T+0 to T+15)

1. T+0: Gate failure is detected, promotion is blocked.
2. T+3: Automatic or manual rollback starts.
3. T+6: Post-rollback verification executes.
4. T+10: Oncall and release owner complete incident review.
5. T+15: Incident summary and next action list are published.
