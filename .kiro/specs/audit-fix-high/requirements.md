# audit-fix-high — 架构审计 High 修复

> **来源**: 2026-03-02 总架构师审计报告
> **优先级**: P1（重要功能缺陷，应尽快修复）
> **预计工时**: 3-5 天

---

## 背景

架构审计发现 5 个 High 级别问题，涉及治理有效性、集成隔离、Console 数据映射。

---

## H1：Heartbeat 事件源 stub 补全

- **现状**：`heartbeat.py` 的 5 个事件源中，webhook / queue / schedule / external_api 四个直接 `return False`
- **问题**：Heartbeat "无事不调 LLM" 的核心机制形同虚设
- **修复策略**：
  - schedule 事件源：接入 Hatchet 调度状态查询，检查是否有到期任务
  - webhook / queue / external_api：保留为可选扩展点，但添加配置开关和文档说明
  - database 事件源：修正 pending/queued 语义（当前 Runtime 不写这些状态）
- **验收**：
  - schedule 事件源能检测到 Hatchet 中的到期调度任务
  - database 事件源使用正确的状态值查询
  - 文档明确说明哪些事件源已实现、哪些是扩展点

## H2：成本追踪实现

- **现状**：所有 Ledger 记录的 `estimated_cost` 为 `Decimal("0")`
- **问题**：BudgetConstraint 基于 Ledger 聚合成本判断超支，但成本永远为 0，预算限制永远不触发
- **修复策略**：
  - 在 `integrations/llm.py` 的 `acompletion` 返回中提取 token usage
  - 使用 litellm 的 `completion_cost()` 计算实际成本
  - 将成本传递到 Ledger 记录
- **验收**：
  - LLM 调用后 Ledger 记录包含非零 `estimated_cost`
  - BudgetConstraint 能基于真实成本触发预算限制
  - mock_mode 下成本为 0（不影响测试）

## H3：litellm embedding 隔离修复

- **现状**：`owlclaw/agent/memory/embedder_litellm.py` 直接 `import litellm` 调用 `litellm.aembedding()`
- **问题**：违反"所有外部库调用必须通过 integrations 层"的架构规则
- **修复策略**：
  - 在 `integrations/llm.py` 添加 `aembedding()` 门面函数
  - 重构 `embedder_litellm.py` 调用门面而非直接调用 litellm
- **验收**：
  - `owlclaw/agent/memory/` 中无直接 `import litellm`
  - embedding 功能正常（现有测试通过）
  - litellm 可被替换而不修改 memory 模块

## H4：Console Governance 前端数据映射修复

- **现状**：
  - 熔断器：后端返回 `capability_name`，前端期望 `name`
  - 可见性矩阵：后端返回扁平 items，前端期望按 agent 分组
- **修复策略**：
  - 在 `useApi.ts` 的 governance hooks 中添加数据转换层
  - 熔断器：`item.capability_name` → `item.name`
  - 可见性矩阵：按 `agent_id` 分组，构建 `{ agent, capabilities: Record<string, boolean> }`
- **验收**：
  - Governance 页面正确显示熔断器名称（非 "unknown"）
  - 可见性矩阵按 Agent 分组显示
  - 契约测试覆盖这两个映射

## H5：治理评估器 fail-open → 可配置策略

- **现状**：`visibility.py:277-284` 评估器异常时 capability 保持可见（fail-open）
- **问题**：安全敏感场景下应 fail-close
- **修复策略**：
  - 添加 `fail_policy` 配置项（`"open"` / `"close"`，默认 `"open"` 保持向后兼容）
  - 异常时根据策略决定 capability 可见性
  - 日志记录异常详情
- **验收**：
  - 默认行为不变（fail-open）
  - 配置 `fail_policy="close"` 后，评估器异常时 capability 被隐藏
  - 两种策略都有测试覆盖

---

## 非功能需求

- 所有修复不得引入新的外部依赖（H3 的 embedding 门面复用现有 litellm 依赖）
- 修复不得改变公共 API 接口（H5 新增配置项为可选参数）
- 所有现有测试必须继续通过
