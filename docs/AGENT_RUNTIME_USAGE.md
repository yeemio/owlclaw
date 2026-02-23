# Agent Runtime Usage Guide

## 1. Prepare App Directory

Required files in app root:
- `SOUL.md`
- `IDENTITY.md`

## 2. Create Runtime

```python
from owlclaw.agent.runtime.runtime import AgentRuntime

runtime = AgentRuntime(
    agent_id="demo-agent",
    app_dir="D:/apps/demo-agent",
    config={
        "model": "gpt-4o-mini",
        "max_function_calls": 10,
        "llm_timeout_seconds": 30,
        "run_timeout_seconds": 120,
        "security": {
            "allow_tools": ["market_scan", "query_state"],
            "max_tool_calls_per_minute": 20,
        },
    },
)
```

## 3. Setup and Run

```python
await runtime.setup()
result = await runtime.trigger_event(
    "cron_tick",
    focus="inventory_monitor",
    payload={"task_type": "analysis"},
    tenant_id="default",
)
print(result)
```

## 4. Config Reload

```python
runtime.load_config_file("D:/apps/demo-agent/runtime.yaml")
runtime.reload_config()
```

## 5. Metrics

```python
metrics = runtime.get_performance_metrics()
print(metrics)
```

## 6. Notes
- Config file path is restricted to `app_dir` subtree.
- Heartbeat trigger skips LLM when no events are pending.
- Runtime writes sanitization and policy-denied actions into security audit log.
