# MCP 能力输出 — 设计文档

> **Spec**: mcp-capability-export
> **阶段**: Phase 8.2
> **接入模式**: 协调模式（Protocol 轨）

---

## 1. 架构概览

```
OpenClaw Agent
    │ MCP Protocol (HTTP/SSE or stdio)
    ▼
OwlClaw MCP Server
    ├── Governance Tools (budget/audit/rate_limit)
    ├── Task Tools (create/status/cancel)
    ├── Business Tools (auto-generated from migrate)
    └── A2A Agent Card (/.well-known/agent.json)
    │
    ├── owlclaw.governance (预算/限流/熔断/审计)
    ├── owlclaw.integrations.hatchet (持久任务)
    └── owlclaw.capabilities.bindings (业务系统连接)
```

## 2. MCP 工具设计

### 2.1 治理工具

| 工具名 | 参数 | 返回 | 说明 |
|--------|------|------|------|
| `governance_budget_status` | `tenant_id?` | `{daily_used, daily_limit, monthly_used, monthly_limit}` | 查询预算使用情况 |
| `governance_audit_query` | `caller?, start_time?, end_time?, limit?` | `[{timestamp, caller, model, tokens, cost, result}]` | 查询审计记录 |
| `governance_rate_limit_status` | `service?` | `{current_qps, limit_qps, rejected_count}` | 查询限流状态 |

### 2.2 持久任务工具

| 工具名 | 参数 | 返回 | 说明 |
|--------|------|------|------|
| `task_create` | `workflow_name, input_data, schedule?` | `{task_id, status}` | 创建持久任务 |
| `task_status` | `task_id` | `{task_id, status, result?, error?}` | 查询任务状态 |
| `task_cancel` | `task_id` | `{task_id, cancelled}` | 取消任务 |

### 2.3 业务工具（自动生成）

`owlclaw migrate --openapi <url> --output-mode mcp` 生成的工具，每个 API endpoint 对应一个 MCP 工具。工具名从 operationId 或路径推导。

## 3. A2A Agent Card

```json
{
  "name": "OwlClaw",
  "description": "AI-powered business system intelligence",
  "url": "https://owlclaw.example.com",
  "version": "0.1.0",
  "capabilities": {
    "governance": ["budget", "rate_limit", "circuit_breaker", "audit"],
    "tasks": ["create", "status", "cancel"],
    "business": ["auto-generated from migrate"]
  },
  "authentication": {
    "schemes": ["bearer"]
  },
  "protocols": {
    "mcp": {"transport": ["http", "stdio"]},
    "a2a": {"version": "0.1.0"}
  }
}
```

静态 JSON 文件，Phase 1 手动维护，Phase 2+ 从注册表自动生成。

## 4. 传输方式

- **HTTP/SSE**：`owlclaw serve --http --port 8080`（远程连接，推荐）
- **stdio**：`owlclaw serve --stdio`（本地桥接，OpenClaw 本地使用）

MCP Spike 需验证哪种方式对 OpenClaw 用户体验更好。

## 5. 安全

所有 MCP 工具调用经过 OwlClaw 治理层：
- 可见性过滤：不同租户/角色看到不同的工具集
- 审计：所有调用记录到 Ledger
- 认证：Bearer token（Phase 1 简单实现）

## 6. 与既有 MCP Server 的关系

本 spec 扩展 mcp-server spec 已有的 MCP Server 实现，新增治理/任务/业务工具。不替换，是增量。

## 7. 测试策略

- **Spike**：OpenClaw → OwlClaw MCP Server → 模拟业务 API 端到端 demo
- **单元测试**：每个 MCP 工具的参数验证和返回格式
- **集成测试**：MCP 工具调用经过治理层的完整链路
- **兼容性测试**：HTTP 和 stdio 两种传输方式
