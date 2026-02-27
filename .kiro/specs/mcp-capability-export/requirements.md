# MCP 能力输出 — 需求文档

> **Spec**: mcp-capability-export
> **阶段**: Phase 8.2
> **决策来源**: `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D4-R (Protocol 轨), D8 (MCP + A2A), D12 (OpenClaw 切入)
> **前置**: mcp-server spec ✅, governance spec ✅, integrations-hatchet spec ✅, declarative-binding spec ✅

---

## 1. 背景

OwlClaw 已有 MCP Server 实现（mcp-server spec ✅）。本 spec 将 OwlClaw 的核心能力（治理、持久任务、业务接入）作为 MCP Server 工具暴露给外部 Agent（特别是 OpenClaw）。

这是 OpenClaw 生态切入的技术基础：OpenClaw 用户通过 MCP 协议调用 OwlClaw 暴露的工具。

## 2. User Stories

### US-1：治理网关 MCP Server
**作为** OpenClaw 用户，**我希望** 通过 MCP 工具调用 OwlClaw 的治理能力（预算查询、限流状态、审计记录），**以便** 在 OpenClaw 中管理 AI 调用成本。

**验收标准**：
- [ ] MCP 工具：`governance_budget_status` — 查询当前预算使用情况
- [ ] MCP 工具：`governance_audit_query` — 查询审计记录
- [ ] MCP 工具：`governance_rate_limit_status` — 查询限流状态
- [ ] OpenClaw 可通过 MCP 连接调用以上工具

### US-2：持久任务 MCP Server
**作为** OpenClaw 用户，**我希望** 通过 MCP 工具创建和管理持久后台任务，**以便** 关掉 OpenClaw 后任务继续执行。

**验收标准**：
- [ ] MCP 工具：`task_create` — 创建持久任务（Hatchet workflow）
- [ ] MCP 工具：`task_status` — 查询任务状态
- [ ] MCP 工具：`task_cancel` — 取消任务
- [ ] 任务在 OpenClaw 关闭后继续执行，完成后可查询结果

### US-3：业务系统接入 MCP Server
**作为** OpenClaw 用户，**我希望** 通过 `owlclaw migrate` 自动生成业务系统的 MCP Server，**以便** 一条命令连上 ERP/CRM/数据库。

**验收标准**：
- [ ] `owlclaw migrate --openapi <url> --output-mode mcp` 生成 MCP Server 工具定义
- [ ] 生成的 MCP Server 可被 OpenClaw 直接连接
- [ ] 配置步骤 ≤ 3 步

### US-4：A2A Agent Card
**作为** 外部 Agent 开发者，**我希望** OwlClaw 暴露标准的 A2A Agent Card，**以便** 发现 OwlClaw 的能力。

**验收标准**：
- [ ] `/.well-known/agent.json` 返回符合 A2A 规范的 Agent Card
- [ ] Agent Card 包含 OwlClaw 的能力列表、认证方式、版本信息

## 3. 非功能需求

- **延迟**：MCP 工具调用 p95 < 500ms
- **兼容性**：MCP Server 支持 HTTP/SSE 和 stdio 两种传输方式
- **安全**：MCP 工具调用经过 OwlClaw 治理层（可见性过滤 + 审计）

## 4. MCP 架构 Spike（Phase 1.5）

在正式开发前需完成技术验证：
- [ ] 验证 `owlclaw serve --http` 暴露的 MCP Server 能否被 OpenClaw 直接连接
- [ ] 验证延迟是否可接受（p95 < 500ms）
- [ ] 验证是否需要 `owlclaw serve --stdio` 本地桥接模式
- [ ] 输出：可运行的 demo + 用户配置文档草稿

## 5. Definition of Done

- [ ] 治理网关 MCP Server 工具可用（3 个工具）
- [ ] 持久任务 MCP Server 工具可用（3 个工具）
- [ ] `owlclaw migrate --output-mode mcp` 可生成业务 MCP Server
- [ ] A2A Agent Card 静态 JSON 可访问
- [ ] OpenClaw 用户 3 步内连上 OwlClaw MCP Server
- [ ] MCP Spike demo 可运行
