# Complete Workflow Example

完整端到端库存管理示例，展示 OwlClaw 从技能定义到业务决策输出的完整链路。

## 场景

本示例覆盖 4 个能力：
- `inventory-check`: 检查低库存 SKU
- `reorder-decision`: 生成补货建议
- `anomaly-alert`: 检测异常消耗并告警
- `daily-report`: 汇总日报

## 架构图（文字版）

```text
heartbeat / manual trigger
        |
        v
   OwlClaw.lite()
        |
        +--> skills/*.md (4 capabilities)
        +--> handlers/*.py (business logic)
        +--> governance (in-memory budget/circuit-breaker)
        |
        v
   decision payloads (JSON)
```

## 运行方法

从仓库根目录执行：

```bash
python examples/complete_workflow/app.py --once
```

输出中会包含 4 个能力的决策结果，其中至少包含 `inventory-check` 与 `reorder-decision` 两个核心决策。

阻塞运行（手动 `Ctrl+C` 退出）：

```bash
python examples/complete_workflow/app.py
```

## 服务化模式 heartbeat 配置（`app.start()`）

把该示例嵌入已有服务时，使用 `await app.start()` 启动。此模式下 heartbeat
需要外部调度器负责周期触发：

```python
import asyncio

from examples.complete_workflow.app import app

async def run_service_mode() -> None:
    runtime = await app.start()
    try:
        while True:
            await runtime.trigger_event("heartbeat", {"source": "service-scheduler"})
            await asyncio.sleep(300)  # 5 minutes
    finally:
        await app.stop()
```

如果需要框架自动心跳循环，请直接运行 `app.run()` 阻塞模式。

## 代码结构

```text
examples/complete_workflow/
├── app.py
├── SOUL.md
├── IDENTITY.md
├── owlclaw.yaml
├── skills/
│   ├── inventory-check/SKILL.md
│   ├── reorder-decision/SKILL.md
│   ├── anomaly-alert/SKILL.md
│   └── daily-report/SKILL.md
└── handlers/
    ├── inventory.py
    ├── reorder.py
    ├── alert.py
    └── report.py
```

## 从 Lite 到生产

1. LLM: 将 Lite mock 切换为真实模型（配置 API Key + model routing）。
2. Memory/Ledger: 从 in-memory 切换到 PostgreSQL（`owlclaw db init/migrate`）。
3. Scheduling: 对接 Hatchet，启用 durable cron 与恢复能力。
4. Observability: 启用 Langfuse/OpenTelemetry 追踪与评估。

## 参考

- [Quick Start](../../docs/QUICK_START.md)
- [Architecture Analysis](../../docs/ARCHITECTURE_ANALYSIS.md)
