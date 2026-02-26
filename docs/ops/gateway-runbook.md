# Gateway Runbook

> Scope: operational runbook for rollout, rollback, and recovery.
> Last Updated: 2026-02-26

## 1. Automatic Rollback Thresholds

Trigger automatic rollback when any condition is met during canary/expansion:

- error rate `> 2%` over active observation window
- p95 latency increase `> 40%` over baseline
- health/readiness probe failure persists for `> 2 minutes`

## 2. Manual Rollback Triggers

Manual rollback is required when:

- alerting pipeline is degraded or unavailable
- security incident is suspected
- data integrity risk is detected by on-call/SRE

Manual rollback requires:

- incident ticket id
- rollback owner
- explicit timestamp in release log

## 3. Post-rollback Verification

After rollback, verify in order:

1. deployment version reverted to prior stable release
2. health and readiness probes recovered
3. error rate and latency back to baseline band
4. no sustained critical alerts for at least 10 minutes

## 4. T+0 ~ T+15 Operational Playbook

- `T+0`: stop promotion and freeze expansion.
- `T+3`: execute rollback and notify release channel.
- `T+6`: verify probes and core SLO metrics.
- `T+10`: complete on-call review and risk assessment.
- `T+15`: publish incident summary and recovery status.

