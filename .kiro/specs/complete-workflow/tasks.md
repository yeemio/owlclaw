# 完整端到端示例 — 任务清单

> **Spec**: complete-workflow
> **创建日期**: 2026-02-25

---

## Task 1: 项目骨架

- [x] 1.1 创建 `examples/complete_workflow/` 目录结构
- [x] 1.2 编写 `SOUL.md`（库存管理 Agent 身份）
- [x] 1.3 编写 `owlclaw.yaml`（Lite Mode 配置 + 治理规则）

## Task 2: Skills 定义

- [x] 2.1 编写 `skills/inventory-check/SKILL.md`
- [x] 2.2 编写 `skills/reorder-decision/SKILL.md`
- [x] 2.3 编写 `skills/anomaly-alert/SKILL.md`
- [x] 2.4 编写 `skills/daily-report/SKILL.md`

## Task 3: Handler 实现

- [x] 3.1 编写 `handlers/__init__.py`
- [x] 3.2 编写 `handlers/inventory.py`（库存检查逻辑）
- [x] 3.3 编写 `handlers/reorder.py`（补货决策逻辑）
- [x] 3.4 编写 `handlers/alert.py`（异常告警逻辑）
- [x] 3.5 编写 `handlers/report.py`（报表生成逻辑）

## Task 4: 主入口

- [x] 4.1 编写 `app.py`（使用 `OwlClaw.lite()`，注册所有 handler，配置 mock_responses）
- [x] 4.2 验证 `python examples/complete_workflow/app.py` 可运行

## Task 5: 文档

- [x] 5.1 编写 `examples/complete_workflow/README.md`（场景说明 + 架构图 + 运行方法）
- [x] 5.2 编写"从 Lite 到生产"迁移指南章节
- [x] 5.3 验证文档无死链接
