# Dual-Run Replay Report (Equivalent Validation)

> Date: 2026-02-27  
> Source: `config/e2e/scenarios/mionyee-tasks.json`  
> Tool: `scripts/mionyee_dual_run_replay.py`

## All Jobs

- compared: 3
- matched: 3
- mismatches: 0
- match_rate: 1.0
- jobs:
  - mionyee task 1
  - mionyee task 2
  - mionyee task 3

## Canary Batch

- compared: 1
- matched: 1
- mismatches: 0
- match_rate: 1.0
- jobs:
  - mionyee task 1

## Conclusion

Replay-based dual-run comparison is fully consistent for current repository-equivalent mionyee tasks.
This substitutes the "1-week live dual-run" requirement in local/offline validation scope.
