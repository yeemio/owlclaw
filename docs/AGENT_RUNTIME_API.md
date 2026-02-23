# Agent Runtime API

## Core Types

### `AgentRunContext`
- `agent_id: str`
- `trigger: str`
- `payload: dict[str, Any]`
- `focus: str | None`
- `tenant_id: str`
- `run_id: str`

### `AgentRuntime`
- `setup() -> None`
- `run(context: AgentRunContext) -> dict[str, Any]`
- `trigger_event(event_name: str, focus: str | None = None, payload: dict | None = None, tenant_id: str = "default") -> dict[str, Any]`
- `load_config_file(path: str) -> dict[str, Any]`
- `reload_config() -> dict[str, Any]`
- `get_performance_metrics() -> dict[str, float]`

## Runtime Return Shape

### Completed
```json
{
  "status": "completed",
  "run_id": "uuid",
  "iterations": 1,
  "final_response": "text",
  "tool_calls_total": 0
}
```

### Skipped (heartbeat)
```json
{
  "status": "skipped",
  "run_id": "uuid",
  "reason": "heartbeat_no_events"
}
```

### Failed (timeout)
```json
{
  "status": "failed",
  "run_id": "uuid",
  "error": "run timed out after 300.0s"
}
```

## Security Config Keys
- `security.allow_tools: list[str]`
- `security.deny_tools: list[str]`
- `security.max_tool_calls_per_minute: int`

## Performance Config Keys
- `performance.max_visible_tools: int`
