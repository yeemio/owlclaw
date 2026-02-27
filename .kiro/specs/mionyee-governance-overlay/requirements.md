# Mionyee 治理叠加 — 需求文档

> **Spec**: mionyee-governance-overlay
> **阶段**: Phase 8.1
> **决策来源**: `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D1-R, D4-R (Handler 轨), D5, D6-R (L3)
> **前置**: governance spec ✅, integrations-hatchet spec ✅, integrations-llm spec ✅

---

## 1. 背景

Mionyee 是 OwlClaw 的第一个 B 段验证基线（有 AI 能力但有瓶颈的 vibecoding 产物）。其 AI 能力现状：
- 28 个 AI 服务，LLM 仅占决策权重 10%
- FinOps 仅观测不执行（内存累加器，无预算上限）
- RBAC 未接入 AI 调用链路
- 无限流、无熔断

本 spec 实现增强模式 Step 1：OwlClaw 治理代理包裹 Mionyee 的 LLM 调用。

## 2. User Stories

### US-1：预算上限拦截
**作为** Mionyee 运维人员，**我希望** 当 LLM 调用累计费用达到日/月预算上限时自动拦截后续调用，**以便** 防止成本失控。

**验收标准**：
- [ ] 配置日预算上限后，超限调用返回治理拦截错误（非 LLM 错误）
- [ ] Ledger 记录拦截事件（含调用方、预算余额、拦截时间）
- [ ] 拦截后 Mionyee 业务逻辑降级到规则模式（不崩溃）

### US-2：限流保护
**作为** Mionyee 运维人员，**我希望** 对 LLM 调用设置 QPS 限流，**以便** 防止突发流量导致 API 配额耗尽。

**验收标准**：
- [ ] 配置 QPS 限流后，超限调用排队或拒绝
- [ ] 限流策略支持按 AI 服务粒度配置
- [ ] Ledger 记录限流事件

### US-3：熔断保护
**作为** Mionyee 运维人员，**我希望** 当 LLM 连续失败达到阈值时自动熔断，**以便** 防止级联故障。

**验收标准**：
- [ ] 配置熔断阈值后，连续失败触发熔断
- [ ] 熔断期间调用直接返回降级响应
- [ ] 熔断恢复后自动半开探测

### US-4：审计完整性
**作为** Mionyee 运维人员，**我希望** 所有 LLM 调用（成功/失败/拦截）都记录到 OwlClaw Ledger，**以便** 事后审计和成本分析。

**验收标准**：
- [ ] 每次 LLM 调用记录：调用方、模型、token 数、费用、延迟、结果
- [ ] 拦截事件记录：拦截原因、治理规则、预算状态
- [ ] 可通过 CLI 查询审计记录

## 3. 非功能需求

- **延迟**：治理判定 p99 < 10ms（走本地缓存）
- **可用性**：OwlClaw 治理层不可用时，Mionyee 降级到无治理模式（不阻塞业务）
- **部署**：Phase 1 采用 sidecar 部署（与 Mionyee 同机），不做独立服务拆分

## 4. Definition of Done

- [ ] Mionyee 的 LLM 调用经过 OwlClaw 治理代理
- [ ] 预算拦截 100% 生效（超限后零 LLM 调用泄漏）
- [ ] 限流生效（QPS 超限时排队或拒绝）
- [ ] 熔断生效（连续失败后自动熔断 + 半开恢复）
- [ ] 审计完整（所有调用/拦截事件可查）
- [ ] Mionyee 业务不受治理层故障影响（降级模式）
- [ ] 治理判定延迟 p99 < 10ms
