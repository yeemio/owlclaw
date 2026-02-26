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
