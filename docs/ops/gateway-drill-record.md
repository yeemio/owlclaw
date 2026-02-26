# Gateway Drill Record

Last updated: 2026-02-26

## Drill 1: Canary Failure Auto Rollback

Command:

```bash
python scripts/ops/gateway_drill_runner.py \
  --scenario canary-fail \
  --metrics-file docs/ops/drills/metrics_canary_fail.json
```

Observed decision:

`rollback`

## Drill 2: Full Rollout Success

Command:

```bash
python scripts/ops/gateway_drill_runner.py \
  --scenario full-success \
  --metrics-file docs/ops/drills/metrics_full_success.json
```

Observed decision:

`promote`

## T+0 to T+15 Tabletop Record

1. T+0: Gate fail detected and promotion blocked.
2. T+3: Rollback action simulated.
3. T+6: Verification checklist executed.
4. T+10: Oncall and release owner review completed.
5. T+15: Drill summary published.
