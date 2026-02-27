# MCP 能力输出 — 任务清单

> **Spec**: mcp-capability-export
> **阶段**: Phase 8.2
> **前置**: mcp-server ✅, governance ✅, integrations-hatchet ✅, declarative-binding ✅

---

## Task 0：Spec 文档与契约

- [x] 0.1 requirements.md / design.md / tasks.md 三层齐全
- [x] 0.2 与 SPEC_TASKS_SCAN.md Phase 8.2 对齐

## Task 1：MCP 架构 Spike

- [x] 1.1 验证 `owlclaw serve --http` 在 OpenClaw 中的连接体验
- [x] 1.2 验证延迟（p95 < 500ms）
- [x] 1.3 验证 stdio 桥接模式是否需要
- [x] 1.4 输出可运行 demo：OpenClaw → OwlClaw MCP Server → 模拟业务 API
- [x] 1.5 输出用户配置文档草稿
- [x] 1.6 决策：默认推荐 HTTP 还是 stdio

## Task 2：治理工具 MCP Server

- [x] 2.1 实现 `governance_budget_status` MCP 工具
- [x] 2.2 实现 `governance_audit_query` MCP 工具
- [x] 2.3 实现 `governance_rate_limit_status` MCP 工具
- [x] 2.4 单元测试：3 个治理工具
  - 文件：`tests/unit/mcp/test_governance_tools.py`

## Task 3：持久任务工具 MCP Server

- [x] 3.1 实现 `task_create` MCP 工具（Hatchet workflow 包装）
- [x] 3.2 实现 `task_status` MCP 工具
- [x] 3.3 实现 `task_cancel` MCP 工具
- [x] 3.4 单元测试：3 个任务工具
  - 文件：`tests/unit/mcp/test_task_tools.py`

## Task 4：业务工具自动生成

- [x] 4.1 扩展 `owlclaw migrate` 支持 `--output-mode mcp`
  - 从 OpenAPI 文档生成 MCP 工具定义
- [x] 4.2 单元测试：MCP 工具生成逻辑
- [x] 4.3 集成测试：生成的 MCP Server 可被 OpenClaw 连接

## Task 5：A2A Agent Card

- [x] 5.1 实现 `/.well-known/agent.json` 静态 JSON 端点
- [x] 5.2 Agent Card 内容符合 A2A v0.1.0 规范
- [x] 5.3 测试：HTTP GET 返回正确的 Agent Card

## Task 6：端到端验收

- [x] 6.1 OpenClaw 用户 3 步内连上 OwlClaw MCP Server
- [x] 6.2 治理工具在 OpenClaw 中可调用
- [x] 6.3 持久任务在 OpenClaw 关闭后继续执行
- [x] 6.4 业务 MCP Server 可被 OpenClaw 发现和使用
