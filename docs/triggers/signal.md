## Signal Trigger Guide

### Overview

Signal trigger provides manual control over running agents. It supports four operations:

- `pause`: stop normal scheduled/event-driven runs.
- `resume`: restore normal runs.
- `trigger`: force one run immediately.
- `instruct`: queue one operator instruction for the next run.

The signal protocol is shared by CLI, HTTP API, and MCP tools.

### CLI Reference

Use `owlclaw agent ...` commands:

- `owlclaw agent pause --agent-id <id> [--tenant-id <tenant>] [--operator <name>]`
- `owlclaw agent resume --agent-id <id> [--tenant-id <tenant>] [--operator <name>]`
- `owlclaw agent trigger --agent-id <id> [--focus <focus>] [--message <msg>]`
- `owlclaw agent instruct --agent-id <id> --message <msg> [--ttl <seconds>]`
- `owlclaw agent status --agent-id <id> [--tenant-id <tenant>]`

All commands are converted to `Signal` objects and dispatched by `SignalRouter`.

### HTTP API

Register admin endpoint on API trigger server:

- `POST /admin/signal`

Typical payload:

```json
{
  "type": "pause",
  "agent_id": "inventory-bot",
  "tenant_id": "default",
  "operator": "ops-oncall",
  "message": "maintenance window"
}
```

When auth is enabled, provide a valid bearer token accepted by the API auth provider.

### MCP Tools

MCP server exposes four tools when `signal_router` is configured:

- `owlclaw_pause`
- `owlclaw_resume`
- `owlclaw_trigger`
- `owlclaw_instruct`

Common arguments:

- `agent_id` (required)
- `tenant_id` (optional, default `default`)
- `operator` (optional, default `mcp`)
- `message` (required for `owlclaw_instruct`)
- `focus` (optional, only for `owlclaw_trigger`)
- `ttl_seconds` (optional, only for `owlclaw_instruct`)

### Runtime Behavior

- For non-manual triggers (for example cron/heartbeat), runtime checks `paused` before decision loop.
- If paused, runtime returns `status=skipped` with reason `agent_paused`.
- `signal_manual` trigger bypasses pause guard.
- Pending instructions are consumed at run start and injected into run payload as `signal_instructions`.
- Ledger records paused-skip and instruction-consumption events when ledger is configured.

### Operator Best Practices

- Use `pause` before risky production changes or incident containment.
- Use `instruct` for short-lived operational guidance instead of hardcoding emergency logic.
- Keep instruction TTL small (for example 10-60 minutes) to avoid stale directives.
- Use `trigger` after `instruct` when immediate execution is required.
- Always include `operator` and `message` for auditability.
