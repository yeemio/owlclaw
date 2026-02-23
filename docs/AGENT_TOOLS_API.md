# Agent Tools API

本文档描述 `owlclaw.agent.tools.BuiltInTools` 的公共接口与内建工具契约。

## 1. BuiltInTools

```python
from owlclaw.agent import BuiltInTools, BuiltInToolsContext
```

### 1.1 构造参数

- `capability_registry`: 提供 `get_state(state_name)` 的对象，用于 `query_state`。
- `ledger`: 提供 `record_execution(**kwargs)` 的对象，用于审计日志。
- `hatchet_client`: 提供调度接口：
  - `schedule_task(task_name, delay_seconds, **payload)`
  - `schedule_cron(workflow_name, cron_name, expression, input_data)`
  - `cancel_task(schedule_id)`
- `memory_system`: 提供记忆接口：
  - `write(content, tags)`
  - `search(query, limit, tags)`
- `scheduled_run_task_name`: 调度任务名，默认 `agent_scheduled_run`。
- `timeout_seconds`: 单次工具调用超时，默认 `30` 秒。
- `max_calls_per_run`: 单次 Agent Run 最大内建工具调用次数，默认 `50`。
- `raise_errors`: 是否抛出严格异常，默认 `False`。
  - `False`: 返回 `{"error": "..."}`
  - `True`: 抛出 `ValueError` / `RuntimeError` / `TimeoutError`

### 1.2 执行入口

```python
result = await tools.execute(tool_name, arguments, context)
```

- `tool_name`: 内建工具名（见下文）。
- `arguments`: JSON object（`dict`）。
- `context`: `BuiltInToolsContext(agent_id, run_id, tenant_id="default")`。

### 1.3 运行期控制

- `is_builtin(tool_name) -> bool`: 判断是否内建工具。
- `get_tool_schemas() -> list[dict]`: 返回 function-calling schemas。
- `reset_run_call_budget(run_id)`: 清理某个 run 的调用计数缓存。

## 2. BuiltInToolsContext

```python
ctx = BuiltInToolsContext(
    agent_id="my-agent",
    run_id="run-001",
    tenant_id="default",
)
```

约束：

- `agent_id`/`run_id`/`tenant_id` 必须是非空字符串。
- 初始化时会自动 `strip()`。

## 3. Built-in Tool Contracts

### 3.1 schedule_once

入参：

- `delay_seconds`: `1..2592000`
- `focus`: 非空字符串

返回（成功）：

```json
{
  "schedule_id": "string",
  "scheduled_at": "in <N> seconds",
  "focus": "string"
}
```

### 3.2 schedule_cron

入参：

- `cron_expression`: 5 段 cron 表达式
- `focus`: 非空字符串

返回（成功）：

```json
{
  "schedule_id": "string",
  "cron_name": "string",
  "cron_expression": "string",
  "focus": "string"
}
```

### 3.3 cancel_schedule

入参：

- `schedule_id`: 非空字符串

返回：

```json
{
  "cancelled": true,
  "schedule_id": "string"
}
```

### 3.4 remember

入参：

- `content`: 非空字符串，最大 2000 字符
- `tags`: 可选字符串数组

返回（成功）：

```json
{
  "memory_id": "string",
  "created_at": "ISO-8601 string",
  "tags": ["tag1", "tag2"]
}
```

### 3.5 recall

入参：

- `query`: 非空字符串
- `limit`: `1..20`，默认 5
- `tags`: 可选字符串数组

返回（成功）：

```json
{
  "memories": [],
  "count": 0
}
```

### 3.6 query_state

入参：

- `state_name`: 非空字符串

返回（成功）：

```json
{
  "state": {}
}
```

### 3.7 log_decision

入参：

- `reasoning`: 非空字符串，最大 1000 字符
- `decision_type`: `capability_selection | schedule_decision | no_action | other`

返回（成功）：

```json
{
  "decision_id": "decision-...",
  "logged": true
}
```

## 4. 示例

- 运行示例：`examples/agent_tools_demo.py`
- 运行命令：

```bash
poetry run python examples/agent_tools_demo.py
```
