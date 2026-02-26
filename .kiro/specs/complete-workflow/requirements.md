# 完整端到端示例 — 需求文档

> **Spec**: complete-workflow
> **创建日期**: 2026-02-25
> **目标**: 创建一个可运行的完整业务场景示例，展示 OwlClaw 全链路能力

---

## 背景

Quick Start 展示最小可用路径，但不足以展示 OwlClaw 的核心价值链：`scan → migrate → SKILL.md → Declarative Binding → Governance → Agent Decision`。需要一个完整的端到端示例，覆盖多个能力、治理规则、触发器配置。

## 功能需求

### FR-1: 示例场景

**库存管理系统**（Inventory Management）：
- 多个业务能力：库存检查、补货决策、异常告警、报表生成
- 治理规则：预算限制、调用频率限制、高风险操作确认
- 触发方式：Heartbeat 定时检查 + API 手动触发

### FR-2: 目录结构

```
examples/complete_workflow/
├── README.md                    # 示例说明文档
├── app.py                       # 主入口
├── SOUL.md                      # Agent 身份
├── owlclaw.yaml                 # 配置文件（Lite Mode）
├── skills/
│   ├── inventory-check/SKILL.md
│   ├── reorder-decision/SKILL.md
│   ├── anomaly-alert/SKILL.md
│   └── daily-report/SKILL.md
└── handlers/
    ├── __init__.py
    ├── inventory.py
    ├── reorder.py
    ├── alert.py
    └── report.py
```

### FR-3: 可运行性

- 使用 Lite Mode，零外部依赖
- `python examples/complete_workflow/app.py` 直接运行
- 运行后可见 Agent 决策日志
- 支持 Ctrl+C 优雅退出

### FR-4: 文档

- `examples/complete_workflow/README.md` 说明：
  - 场景描述
  - 架构图（文字版）
  - 运行方法
  - 代码结构解释
  - 如何扩展到生产环境（切换到真实 LLM、PostgreSQL、Hatchet）

## 验收标准

1. `python examples/complete_workflow/app.py` 可运行
2. 日志输出展示至少 2 个不同能力的决策过程
3. README.md 完整且无死链接
4. 代码符合项目规范（绝对导入、类型注解、无 TODO）
