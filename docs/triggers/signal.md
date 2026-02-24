# Signal Trigger Guide

## Overview

Signal trigger provides manual intervention controls for a running agent:

- pause autonomous runs
- resume autonomous runs
- force trigger one run
- queue operator instructions for next run

Signal requests from CLI, HTTP API, and MCP are normalized to the same `Signal` model and dispatched by `SignalRouter`.

## Data Flow

1. Client sends one signal operation (`pause|resume|trigger|instruct`).
2. Entry adapter converts request into `Signal(source=cli|api|mcp, ...)`.
3. `SignalRouter.dispatch()` validates, routes, and records ledger entry.
4. Handler updates state (`paused`, `pending_instructions`) or triggers runtime.

## CLI Reference

All commands support `--agent-id` (and backward-compatible `--agent`):

```bash
owlclaw agent pause --agent-id <id> [--tenant default] [--operator cli]
owlclaw agent resume --agent-id <id> [--tenant default] [--operator cli]
owlclaw agent trigger --agent-id <id> [--message "..."] [--focus "..."] [--tenant default] [--operator cli]
owlclaw agent instruct --agent-id <id> --message "..." [--ttl 3600] [--tenant default] [--operator cli]
owlclaw agent status --agent-id <id> [--tenant default]
```

## HTTP API Entry

`APITriggerServer.register_signal_admin(...)` mounts a shared Starlette endpoint:

- `POST /admin/signal`
- Bearer authentication via existing API auth provider
- request body validation by `SignalAPIRequest` (Pydantic)

Example request:

```json
{
  "type": "instruct",
  "agent_id": "trading-bot",
  "tenant_id": "default",
  "operator": "ops",
  "message": "暂停买入，等待风控确认",
  "ttl_seconds": 3600
}
```

## MCP Integration

`register_signal_mcp_tools()` registers 4 MCP tools through capability registry:

- `owlclaw_pause`
- `owlclaw_resume`
- `owlclaw_trigger`
- `owlclaw_instruct`

All tools convert arguments to `Signal(source=MCP)` and call `SignalRouter.dispatch()`.

## Runtime Integration

When `AgentRuntime` is provided with `signal_state_manager`:

- autonomous triggers (`heartbeat` and payload `trigger_type=cron`) are skipped when agent state is paused
- signal manual trigger (`trigger="signal_manual"`) bypasses paused check
- pending instructions are consumed at run start and injected into `context.payload["operator_instructions"]`

## Operational Best Practices

Use pause when:

- market/system condition is unstable and autonomous behavior must stop
- maintenance window requires deterministic freeze

Use instruct when:

- an operator decision must be applied once in the next run
- short-term policy override is needed with explicit TTL

Use trigger when:

- a run is required immediately regardless of paused autonomous schedule

Avoid:

- long-lived instructions with no TTL discipline
- bypassing router/state manager by direct state table writes
