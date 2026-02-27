# OpenClaw MCP Spike Report

## Scope

This spike validates Phase 8.2 Task 1 for MCP connection experience:

1. OpenClaw-compatible HTTP MCP endpoint is reachable.
2. p95 latency target is below 500ms.
3. stdio bridge remains available as local fallback.
4. A runnable demo and a draft user config are available.
5. Default transport recommendation is documented.

## Artifacts

- HTTP transport adapter: `owlclaw/mcp/http_transport.py`
- Runnable demo + benchmark: `scripts/mcp_spike_demo.py`
- Integration test:
  - `tests/integration/test_mcp_spike_transport_integration.py`
  - `tests/integration/test_mcp_generated_tools_integration.py`

## Validation Result (2026-02-27)

Command:

```bash
poetry run python scripts/mcp_spike_demo.py --iterations 120
```

Observed output:

```json
{
  "http_p95_ms": 2.11,
  "stdio_p95_ms": 3.02
}
```

Both transports are below the target `p95 < 500ms`.

## OpenClaw User Config Draft (3 steps)

1. Start an OwlClaw MCP HTTP app (or embed into your existing service) exposing:
   - `POST /mcp`
   - `GET /.well-known/agent.json`
2. In OpenClaw MCP settings, add server URL: `http://<host>:<port>/mcp`
3. Verify with one tool call (`tools/list` then `tools/call`) and check that `agent.json` is reachable.

## Transport Decision

- **Default recommendation: HTTP**
  - Better interoperability with OpenClaw and remote agents.
  - Fits deployment and network debugging workflows.
- **Fallback: stdio**
  - Keep for local, single-process, no-network scenarios.
  - Useful when embedding MCP in local tooling pipelines.
