# Gateway Rollout Policy

> Scope: staged rollout policy for API/MCP gateway changes.
> Last Updated: 2026-02-26

## 1. Rollout Ratios

Default staged rollout:

1. canary: `5%`
2. expansion: `25%`
3. full rollout: `100%`

High-risk changes (protocol or auth model change):

1. canary: `1%`
2. expansion: `10%`
3. full rollout: `100%`

## 2. Observation Windows

- canary minimum observation window: `10 minutes`
- expansion minimum observation window: `15 minutes`
- full rollout verification window: `30 minutes`

No stage promotion is allowed before the minimum window closes.

## 3. Promotion and Block Conditions

Promotion requires all conditions:

- error rate `<= 2%`
- p95 latency increase `<= 40%` versus baseline
- no sustained critical alerts in current window

Block conditions:

- missing metrics for required SLO signals
- alerting pipeline unavailable
- rollback in progress

When blocked, rollout stops at current stage and requires on-call review.

## 4. Approval Boundaries

- automatic promotion: canary -> expansion only when all SLO checks pass
- manual approval required: expansion -> full rollout for high-risk changes
- manual override must include incident/reference ticket and audit note

