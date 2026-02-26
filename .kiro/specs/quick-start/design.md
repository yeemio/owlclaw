# Quick Start 指南 — 设计文档

> **Spec**: quick-start
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 基于 Lite Mode

Quick Start 全程使用 `OwlClaw.lite()` 启动，确保零外部依赖：
- LLM：mock mode（无需 API Key）
- Memory：in-memory store（无需 PostgreSQL）
- Governance：InMemoryLedger（预算/限流/熔断全部可用）
- Scheduler：无 Hatchet（cron 触发器跳过）

### D-2: 示例场景选择

选择"库存检查"作为 Quick Start 场景：
- 业务直觉强（任何人都理解"库存不足需要补货"）
- 展示核心链路：事件触发 → Agent 决策 → 工具调用
- 代码量小（一个 handler，一个 SKILL.md）

### D-3: 文档结构

```
docs/QUICK_START.md          # 主文档
examples/quick_start/
├── app.py                   # 入口（~30 行）
├── SOUL.md                  # Agent 身份
└── skills/
    └── inventory-check/
        └── SKILL.md         # 库存检查能力描述
```

### D-4: app.py 核心代码

```python
from owlclaw import OwlClaw

app = OwlClaw.lite("inventory-agent", skills_path="./skills/")

@app.handler("inventory-check")
async def check_inventory(session) -> dict:
    return {"action": "reorder", "sku": "WIDGET-42", "quantity": 100}

if __name__ == "__main__":
    app.run()
```

### D-5: 日志输出

运行后用户应看到类似输出：
```
OwlClaw 'inventory-agent' created in Lite Mode
Starting OwlClaw application 'inventory-agent'
OwlClaw 'inventory-agent' is running (heartbeat=5min). Press Ctrl+C to stop.
```

## 依赖

- `OwlClaw.lite()` 类方法（Phase B2 已实现）
- `InMemoryLedger`（Phase B2 已实现）
- `app.run()` 阻塞式启动（Phase B1 已实现）

## 不做

- 不涉及数据库配置
- 不涉及 Hatchet 配置
- 不涉及真实 LLM API Key
