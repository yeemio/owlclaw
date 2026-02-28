# How to connect OpenClaw to your business database in one command

This guide shows how to connect OpenClaw to OwlClaw MCP tools in three steps:

1. install skill package
2. configure one endpoint
3. call governance and task tools

Estimated time: 10 minutes.

## Problem

OpenClaw users often have prompt power but lack:

- governance visibility (budget, audit, rate limit)
- durable background jobs
- fast path to expose existing business APIs as tools

`owlclaw-for-openclaw` solves this by packaging an MCP-ready skill.

## Step 1: install the skill package

Install `owlclaw-for-openclaw` in ClawHub.

Package path in this repository:

- `skills/owlclaw-for-openclaw/`

## Step 2: configure one MCP endpoint

Set one env var:

```bash
export OWLCLAW_MCP_ENDPOINT=http://127.0.0.1:8080/mcp
```

Use the sample config:

```json
{
  "mcpServers": {
    "owlclaw": {
      "transport": "http",
      "url": "${OWLCLAW_MCP_ENDPOINT}",
      "agentCardUrl": "http://127.0.0.1:8080/.well-known/agent.json"
    }
  }
}
```

## Step 3: use tools from OpenClaw

Example prompts:

- "Check budget usage for tenant `t-1` and agent `openclaw-agent`."
- "Create a background task named `nightly_sync`."
- "Show task status for `<task_id>`."

Expected behavior:

- OpenClaw discovers `governance_*` and `task_*` tools
- tool calls are executed through OwlClaw MCP

## Reproducibility log

This tutorial flow is validated by automated tests in this repository:

- `tests/integration/test_mcp_openclaw_e2e_acceptance.py`
- `tests/integration/test_openclaw_skill_compatibility.py`
- `tests/unit/test_openclaw_skill.py`

Validation date: 2026-02-28.
