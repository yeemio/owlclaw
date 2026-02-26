# 完整端到端示例 — 设计文档

> **Spec**: complete-workflow
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 基于 Lite Mode + 配置文件

示例使用 `OwlClaw.lite()` 启动，同时展示 `owlclaw.yaml` 配置文件的用法：
- 治理规则通过配置文件定义
- mock_responses 按 task_type 定制，模拟真实 LLM 决策

### D-2: 四个业务能力

| 能力 | task_type | 说明 |
|------|-----------|------|
| inventory-check | monitor | 检查库存水位，返回低库存 SKU 列表 |
| reorder-decision | decision | 根据库存数据决定是否补货 |
| anomaly-alert | alert | 检测异常模式（如突然大量消耗） |
| daily-report | report | 生成每日库存摘要 |

### D-3: 治理规则展示

```yaml
governance:
  use_inmemory_ledger: true
  visibility:
    budget:
      high_cost_threshold: "0.5"
      budget_limits:
        inventory-agent: "10.0"
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 60
```

### D-4: Handler 实现

每个 handler 返回结构化决策结果，模拟真实业务逻辑：

```python
@app.handler("inventory-check")
async def check_inventory(session) -> dict:
    return {
        "low_stock_items": [
            {"sku": "WIDGET-42", "current": 5, "threshold": 20},
            {"sku": "GADGET-99", "current": 12, "threshold": 50},
        ],
        "action": "trigger_reorder_review",
    }
```

### D-5: 从 Lite 到生产的迁移指南

README 中包含"切换到生产环境"章节，说明如何：
1. 替换 mock LLM → 真实 API Key
2. 替换 in-memory → PostgreSQL
3. 添加 Hatchet 持久执行
4. 配置 Langfuse 可观测

## 依赖

- `OwlClaw.lite()` + `InMemoryLedger`（Phase B2）
- `app.run()`（Phase B1）
- `owlclaw.yaml` 配置系统（configuration spec ✅）
- SKILL.md 格式（capabilities-skills spec ✅）
