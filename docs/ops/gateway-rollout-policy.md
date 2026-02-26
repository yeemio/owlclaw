# Gateway Rollout Policy

Last updated: 2026-02-26

## Scope

This policy defines staged rollout gates for gateway-facing changes (API and MCP paths).

## Staged Ratios

1. Canary: 5%
2. Expansion: 25%
3. Full rollout: 100%

## Observation Windows

1. Canary window: 10 minutes minimum
2. Expansion window: 15 minutes minimum
3. Full rollout verification window: 15 minutes minimum

## Promotion Criteria

All criteria must pass in the current stage window:

1. 5xx error rate <= 2.0%
2. P95 latency regression <= 40% versus baseline
3. Readiness probe success rate >= 99.5%
4. No unresolved `critical` alerts

## Block Conditions

Any single condition blocks promotion:

1. 5xx error rate > 2.0%
2. P95 latency regression > 40%
3. Missing metrics for required probes
4. Alerting pipeline unavailable

## Auto vs Manual Promotion Boundary

1. Canary to expansion can be automated after all promotion criteria pass.
2. Expansion to full rollout requires manual approval when any warning alert was active in the window.
3. Full rollout requires manual approval if there was a rollback in the last 24 hours.

## Evidence Requirements

Each stage must archive:

1. Gate decision summary
2. Dashboard snapshot link
3. Alert status summary
4. Run identifier and commit SHA
