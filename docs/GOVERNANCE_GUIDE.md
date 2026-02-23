# Governance Guide

本指南覆盖 OwlClaw 治理层（VisibilityFilter、Ledger、Router）的 API、配置、集成方式与排障要点。

## 1. API 文档

### 1.1 VisibilityFilter

- 类型：`owlclaw.governance.visibility.VisibilityFilter`
- 关键方法：
  - `register_evaluator(evaluator)`：注册约束评估器，要求实现 `evaluate(capability, agent_id, context)`。
  - `filter_capabilities(capabilities, agent_id, context)`：并行评估约束，返回可见能力列表。
- 关键行为：
  - 评估器异常时 `fail-open`（能力保持可见）并记录日志。
  - 高风险能力默认走 `RiskGate`，未确认能力会被过滤。

### 1.2 Ledger

- 类型：`owlclaw.governance.ledger.Ledger`
- 关键方法：
  - `record_execution(...)`：异步入队能力执行记录，不阻塞主流程。
  - `start()` / `stop()`：启动/停止后台批量写入任务。
  - `query_records(tenant_id, filters)`：按租户强制隔离查询执行记录。
  - `get_cost_summary(tenant_id, agent_id, start_date, end_date)`：返回总成本、按 Agent 统计、按能力统计。
- 关键行为：
  - 后台写入失败时自动重试 3 次（指数退避）后降级写入 `ledger_fallback.log`。
  - 所有查询均以 `tenant_id` 作为强制过滤条件。

### 1.3 Router

- 类型：`owlclaw.governance.router.Router`
- 关键方法：
  - `select_model(task_type, context)`：按 `task_type` 匹配模型和降级链。
  - `handle_model_failure(failed_model, task_type, error, fallback_chain)`：返回下一个可用模型。
  - `reload_config(config)`：运行时热重载路由规则与默认模型。

## 2. 配置文档

治理配置位于 `owlclaw.yaml` 的 `governance` 节点（示例）：

```yaml
governance:
  visibility:
    budget:
      high_cost_threshold: 0.1
      budget_limits:
        trader-agent: 100
    time:
      timezone: Asia/Shanghai
      trading_hours:
        start: "09:30"
        end: "15:00"
        weekdays: [0, 1, 2, 3, 4]
  router:
    default_model: gpt-4o-mini
    rules:
      - task_type: trading_decision
        model: gpt-4o
        fallback: [gpt-4o-mini, gpt-4.1-mini]
```

说明：

- `governance.visibility`：控制能力可见性约束（预算/时间/限流/熔断/确认）。
- `governance.router`：控制模型选择与降级策略。
- Ledger 依赖数据库连接（`OWLCLAW_DATABASE_URL`）和 Alembic 迁移。

## 3. 集成指南

### 3.1 初始化与启动

1. 完成数据库迁移：`alembic -c alembic.ini upgrade head`
2. 在应用配置中启用 `governance.visibility` 与 `governance.router`
3. 启动应用时调用治理初始化（`app._ensure_governance()`）并启动 ledger 后台任务（`app.start_governance()`）

### 3.2 运行时流程

1. Agent Run 开始前：
   - `VisibilityFilter.filter_capabilities` 过滤可用能力
   - `Router.select_model` 按任务类型选模型
2. Agent 执行后：
   - `Ledger.record_execution` 记录执行数据（模型、token、成本、状态）
3. 应用停止时：
   - `app.stop_governance()` 停止后台写入任务

### 3.3 热更新

- 配置更新后可调用 `Router.reload_config(new_router_config)` 热重载路由。
- 可结合配置监听器，在配置变更时自动刷新治理配置。

## 4. 故障排查指南

### 4.1 迁移失败

- 现象：`alembic upgrade head` 报错。
- 检查：
  - `OWLCLAW_DATABASE_URL` 是否为 PostgreSQL 地址。
  - 数据库是否可连接、权限是否允许建表/建索引/创建扩展。
  - 迁移链版本是否完整（`001_initial -> 002_ledger -> 003_memory`）。

### 4.2 Ledger 写入失败

- 现象：日志出现 `Failed to flush ledger batch`。
- 检查：
  - 数据库连接池状态与事务错误。
  - 是否持续降级写入 `ledger_fallback.log`。
  - 应用是否调用了 `start_governance()` 启动后台任务。

### 4.3 能力被意外过滤

- 现象：预期能力未出现在可见列表。
- 检查：
  - 能力 `risk_level` 与 `requires_confirmation` 配置。
  - `RunContext.confirmed_capabilities` 是否包含该能力名。
  - 预算、时段、限流、熔断约束是否命中。

### 4.4 模型选择异常

- 现象：总是走默认模型或无法降级。
- 检查：
  - `router.rules[].task_type` 是否与运行时任务类型一致。
  - `fallback` 是否为非空字符串列表。
  - 配置更新后是否执行了 `reload_config`。
