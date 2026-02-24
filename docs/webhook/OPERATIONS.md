# Webhook Operations Guide

## Monitoring

Use gateway endpoints:
- `GET /health` for dependency health
- `GET /metrics` for realtime counters and latency aggregates
- `GET /events` for event log query

## Alerting

Built-in monitoring triggers alerts for:
- high failure rate
- high response time

Alert dedup window is configurable in monitoring service.

## Troubleshooting

Common HTTP errors:
- `400`: payload format / schema issues
- `401`: auth token invalid
- `403`: signature/governance rejection
- `404`: unknown endpoint
- `429`: rate limit exceeded
- `503`: runtime/governance unavailable

Check sequence:
1. Verify endpoint exists and enabled.
2. Verify auth headers/signature.
3. Inspect `/events?request_id=...`.
4. Inspect `/metrics` and alert stream.

## Performance Tuning

- Raise `per_ip_limit_per_minute` and `per_endpoint_limit_per_minute` carefully.
- Adjust retry policy for transient runtime failures.
- Prefer async execution mode for high-throughput use.

## Backup and Recovery

- Backup database tables:
  - `webhook_endpoints`
  - `webhook_events`
  - `webhook_idempotency_keys`
  - `webhook_transformation_rules`
  - `webhook_executions`
- Restore schema via migration tool, then restore data dump.
