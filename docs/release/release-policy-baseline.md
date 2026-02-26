# Release Policy Baseline

Last updated: 2026-02-26

## Required Checks Baseline

The calibrated required checks baseline for `main` is:

1. `Lint`
2. `Test`
3. `Build`

## Branch Protection Baseline

Recommended `main` protection baseline:

1. Require pull request before merge
2. Required approving reviews: 1
3. Dismiss stale reviews: enabled
4. Require code owner review: enabled
5. Enforce for admins: enabled
6. Strict required status checks: enabled

## Drift Note

As of audit timestamp, `main` is unprotected in remote configuration.
Use `scripts/ops/release_policy_audit.py` output as evidence and remediation input.
