# audit-fix-high — 设计文档

---

## H1：Heartbeat 事件源补全

### 变更范围

**文件**：`owlclaw/agent/runtime/heartbeat.py`

### schedule 事件源实现

```python
async def _check_schedule_events(self) -> bool:
    """Check if any scheduled tasks are due via Hatchet."""
    try:
        from owlclaw.integrations.hatchet import get_hatchet_client
        client = get_hatchet_client()
        if client is None:
            return False
        scheduled = await client.list_scheduled_tasks(agent_id=self._agent_id)
        return any(task.is_due() for task in scheduled)
    except Exception:
        logger.warning("heartbeat.schedule_check_failed", agent_id=self._agent_id)
        return False
```

### database 事件源修正

当前检查 `status.in_(["pending", "queued"])`，但 Runtime 不写这些状态。修改为检查最近时间窗口内是否有需要关注的记录（如 `"error"` 状态需要重试）。

### webhook / queue / external_api

保留为扩展点，添加 `@abstractmethod` 或配置开关：
- 若配置启用但未实现 → 日志 warning + return False
- 文档明确标注为"可选扩展点"

---

## H2：成本追踪

### 变更范围

**文件**：
- `owlclaw/integrations/llm.py` — 提取 token usage 和计算成本
- `owlclaw/agent/runtime/runtime.py` — 传递成本到 Ledger

### 设计

1. `acompletion()` 返回值中提取 `response.usage`（prompt_tokens, completion_tokens）
2. 使用 `litellm.completion_cost(response)` 计算成本（litellm 内置各模型定价）
3. 返回 `CostInfo(prompt_tokens, completion_tokens, total_cost)` dataclass
4. Runtime 在 `_record_ledger()` 时传入 `estimated_cost=cost_info.total_cost`
5. mock_mode 下返回 `CostInfo(0, 0, Decimal("0"))`

---

## H3：Embedding 隔离

### 变更范围

**文件**：
- `owlclaw/integrations/llm.py` — 新增 `aembedding()` 门面
- `owlclaw/agent/memory/embedder_litellm.py` — 改用门面

### 设计

```python
# integrations/llm.py
async def aembedding(model: str, input: list[str], **kwargs) -> list[list[float]]:
    """Facade for embedding calls, same pattern as acompletion."""
    import litellm
    response = await litellm.aembedding(model=model, input=input, **kwargs)
    return [item["embedding"] for item in response.data]
```

```python
# agent/memory/embedder_litellm.py (修改后)
from owlclaw.integrations.llm import aembedding
# 不再 import litellm
```

---

## H4：Console Governance 数据映射

### 变更范围

**文件**：`owlclaw/web/frontend/src/hooks/useApi.ts`

### 熔断器映射

```typescript
// useCircuitBreakers() 返回数据转换
const normalized = data.items.map(item => ({
  ...item,
  name: item.capability_name ?? item.name,
}));
```

### 可见性矩阵映射

```typescript
// useVisibilityMatrix() 返回数据转换
const grouped = Object.entries(
  groupBy(data.items, item => item.agent_id)
).map(([agent, items]) => ({
  agent,
  capabilities: Object.fromEntries(
    items.map(i => [i.capability_name, i.visible])
  ),
}));
```

---

## H5：治理 fail-policy 配置

### 变更范围

**文件**：`owlclaw/governance/visibility.py`

### 设计

```python
class VisibilityFilter:
    def __init__(self, evaluators, fail_policy: str = "open"):
        self._fail_policy = fail_policy  # "open" or "close"

    async def _evaluate_single(self, evaluator, capability, context):
        try:
            return await evaluator.evaluate(capability, context)
        except Exception as exc:
            logger.error("evaluator_failed", evaluator=type(evaluator).__name__, exc=str(exc))
            if self._fail_policy == "close":
                return EvaluationResult(visible=False, reason=f"evaluator error: {exc}")
            return EvaluationResult(visible=True, reason="evaluator error (fail-open)")
```
