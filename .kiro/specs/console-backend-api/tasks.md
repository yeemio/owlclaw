# Tasks: Console Backend API

> **Spec**: console-backend-api  
> **Design**: `design.md`  
> **最后更新**: 2026-02-28

---

## Task 0：查询契约层 + 包结构

**目标**：创建 `owlclaw/web/` 包结构和全部 Protocol 定义

**文件**：
- `owlclaw/web/__init__.py`
- `owlclaw/web/contracts.py`
- `owlclaw/web/api/__init__.py`
- `owlclaw/web/providers/__init__.py`

**实现**：
- [ ] 0.1 创建 `owlclaw/web/` 包结构（`__init__.py` + `contracts.py` + `api/` + `providers/`）
- [ ] 0.2 实现 `contracts.py`：定义 `OverviewProvider`、`GovernanceProvider`、`TriggersProvider`、`AgentsProvider`、`CapabilitiesProvider`、`LedgerProvider`、`SettingsProvider` 共 7 个 Protocol 接口
- [ ] 0.3 定义共享数据类：`HealthStatus`、`OverviewMetrics`、`PaginatedResult`

**验收**：
- `from owlclaw.web.contracts import OverviewProvider` 可导入
- 所有 Protocol 有完整类型注解
- `poetry run mypy owlclaw/web/contracts.py` 通过

---

## Task 1：API 框架（路由 + 认证 + 错误处理 + 分页）

**目标**：搭建 FastAPI 应用框架

**文件**：
- `owlclaw/web/api/__init__.py` — `create_api_app()` 工厂
- `owlclaw/web/api/middleware.py` — Token 认证 + CORS
- `owlclaw/web/api/schemas.py` — 统一响应模型
- `owlclaw/web/api/deps.py` — 依赖注入
- `owlclaw/web/app.py` — `create_console_app()` 组装入口

**实现**：
- [ ] 1.1 实现 `create_api_app()` 工厂函数，挂载到 `/api/v1/` 前缀
- [ ] 1.2 实现 `TokenAuthMiddleware`：从 `OWLCLAW_CONSOLE_TOKEN` 读取，空则跳过认证
- [ ] 1.3 实现 CORS 中间件配置（`OWLCLAW_CONSOLE_CORS_ORIGINS`）
- [ ] 1.4 实现统一错误处理（`ErrorResponse` 格式 + 全局异常处理器）
- [ ] 1.5 实现 `PaginatedResponse` 通用分页响应模型
- [ ] 1.6 实现 `deps.py` Provider 注册表和 `Depends` 函数
- [ ] 1.7 实现 `create_console_app()` 组装 Provider 实例并创建 FastAPI 应用
- [ ] 1.8 OpenAPI Schema 自动生成验证（`/api/v1/openapi.json` 可访问）

**验收**：
- `GET /api/v1/openapi.json` 返回 200
- 无 Token 时 `GET /api/v1/overview` 返回 401（当 `OWLCLAW_CONSOLE_TOKEN` 已设置）
- 有效 Token 时返回 200
- `poetry run pytest tests/unit/web/test_middleware.py` 通过

---

## Task 2：Overview API + Provider

**目标**：系统健康和关键指标

**文件**：
- `owlclaw/web/providers/overview.py` — `DefaultOverviewProvider`
- `owlclaw/web/api/overview.py` — Overview 路由

**实现**：
- [ ] 2.1 实现 `DefaultOverviewProvider`：聚合 Runtime/DB/Hatchet/LLM/Langfuse 连通性检查
- [ ] 2.2 实现今日成本/执行次数/成功率/活跃 Agent 指标聚合（从 Ledger 查询）
- [ ] 2.3 实现 `GET /api/v1/overview` 路由
- [ ] 2.4 Overview 指标缓存（TTL 30s，避免频繁聚合查询）

**验收**：
- `GET /api/v1/overview` 返回 `OverviewMetrics` 结构
- 各组件连通性状态正确反映
- 缓存生效（30s 内重复请求不触发底层查询）
- `poetry run pytest tests/unit/web/test_overview.py` 通过

---

## Task 3：Governance API + Provider

**目标**：治理数据聚合

**文件**：
- `owlclaw/web/providers/governance.py` — `DefaultGovernanceProvider`
- `owlclaw/web/api/governance.py` — Governance 路由

**实现**：
- [ ] 3.1 实现 `DefaultGovernanceProvider`：预算消耗趋势（按天/周/月聚合）
- [ ] 3.2 实现限流/熔断状态查询
- [ ] 3.3 实现能力可见性矩阵（Agent × Capability）
- [ ] 3.4 实现 `GET /api/v1/governance/budget`、`GET /api/v1/governance/circuit-breakers`、`GET /api/v1/governance/visibility-matrix` 路由

**验收**：
- 预算趋势返回按时间粒度聚合的数据
- 熔断器状态包含 open/closed/half-open
- 可见性矩阵正确反映 VisibilityFilter 结果
- `poetry run pytest tests/unit/web/test_governance.py` 通过

---

## Task 4：Ledger API + Provider

**目标**：执行审计数据

**文件**：
- `owlclaw/web/providers/ledger.py` — `DefaultLedgerProvider`
- `owlclaw/web/api/ledger.py` — Ledger 路由

**实现**：
- [ ] 4.1 实现 `DefaultLedgerProvider`：多维筛选 + 分页 + 排序
- [ ] 4.2 实现记录详情查询（输入/输出/成本/模型/延迟/决策推理）
- [ ] 4.3 实现 `GET /api/v1/ledger`（列表 + 筛选 + 分页）和 `GET /api/v1/ledger/{id}`（详情）路由

**验收**：
- 筛选参数（agent_id/capability/时间/成本/状态）正确过滤
- 分页返回 `{ items, total, offset, limit }`
- 详情包含完整执行信息
- `poetry run pytest tests/unit/web/test_ledger.py` 通过

---

## Task 5：Capabilities API + Provider

**目标**：能力注册信息

**文件**：
- `owlclaw/web/providers/capabilities.py` — `DefaultCapabilitiesProvider`
- `owlclaw/web/api/capabilities.py` — Capabilities 路由

**实现**：
- [ ] 5.1 实现 `DefaultCapabilitiesProvider`：从 CapabilityRegistry 获取 Handlers/Skills/Bindings 分类列表
- [ ] 5.2 实现 JSON Schema 查看
- [ ] 5.3 实现调用统计（从 Ledger 聚合）
- [ ] 5.4 实现 `GET /api/v1/capabilities`（列表 + 分类筛选）和 `GET /api/v1/capabilities/{name}/schema`（Schema 查看）路由

**验收**：
- 列表按 handler/skill/binding 分类
- Schema 返回 JSON Schema 格式
- 调用统计包含执行次数、成功率、平均延迟
- `poetry run pytest tests/unit/web/test_capabilities.py` 通过

---

## Task 6：Triggers API + Provider

**目标**：触发器统一状态

**文件**：
- `owlclaw/web/providers/triggers.py` — `DefaultTriggersProvider`
- `owlclaw/web/api/triggers.py` — Triggers 路由

**实现**：
- [ ] 6.1 实现 `DefaultTriggersProvider`：聚合 6 类触发器状态（cron/webhook/queue/db_change/api/signal）
- [ ] 6.2 实现执行历史查询
- [ ] 6.3 实现 `GET /api/v1/triggers`（统一列表）和 `GET /api/v1/triggers/{id}/history`（执行历史）路由

**验收**：
- 6 类触发器在统一格式中返回
- 每个触发器包含 type/enabled/next_run/success_rate
- 执行历史支持分页
- `poetry run pytest tests/unit/web/test_triggers.py` 通过

---

## Task 7：Agents API + Provider

**目标**：Agent 列表和详情

**文件**：
- `owlclaw/web/providers/agents.py` — `DefaultAgentsProvider`
- `owlclaw/web/api/agents.py` — Agents 路由

**实现**：
- [ ] 7.1 实现 `DefaultAgentsProvider`：Agent 列表（身份配置 + 记忆统计 + 知识库挂载）
- [ ] 7.2 实现 Agent 详情（运行历史从 Ledger 聚合）
- [ ] 7.3 实现 `GET /api/v1/agents`（列表）和 `GET /api/v1/agents/{id}`（详情）路由

**验收**：
- Agent 列表包含身份信息（SOUL.md 摘要）
- 详情包含运行历史时间线
- `poetry run pytest tests/unit/web/test_agents.py` 通过

---

## Task 8：Settings API + Provider

**目标**：运行时配置和系统信息

**文件**：
- `owlclaw/web/providers/settings.py` — `DefaultSettingsProvider`
- `owlclaw/web/api/settings.py` — Settings 路由

**实现**：
- [ ] 8.1 实现 `DefaultSettingsProvider`：运行时配置（只读，敏感字段脱敏）
- [ ] 8.2 实现 MCP Server 状态 + DB 迁移版本 + 版本号/构建时间/commit hash
- [ ] 8.3 实现 OwlHub 连接状态
- [ ] 8.4 实现 `GET /api/v1/settings` 路由

**验收**：
- 敏感字段（API key、密码）显示为 `***`
- 版本信息正确
- MCP 状态反映实际连接
- `poetry run pytest tests/unit/web/test_settings.py` 通过

---

## Task 9：WebSocket 实时推送

**目标**：关键指标和事件的实时流

**文件**：
- `owlclaw/web/api/ws.py` — WebSocket 路由

**实现**：
- [ ] 9.1 实现 WebSocket 端点 `/api/v1/ws`（认证 + 连接管理）
- [ ] 9.2 实现 Overview 指标定时推送（30s 间隔）
- [ ] 9.3 实现 Trigger 事件推送
- [ ] 9.4 实现 Ledger 新记录推送

**验收**：
- WebSocket 可连接并接收 JSON 消息
- 连接数限制生效（默认 10）
- 断线重连不导致资源泄漏
- `poetry run pytest tests/unit/web/test_ws.py` 通过

---

## Task 10：架构隔离验证 + 集成测试

**目标**：确保架构隔离约束和整体集成

**文件**：
- `tests/unit/web/test_architecture_isolation.py` — 导入扫描
- `tests/integration/test_console_api.py` — 集成测试

**实现**：
- [ ] 10.1 实现 AST 导入扫描：验证 `owlclaw/web/api/` 中无 `from owlclaw.agent`、`from owlclaw.governance`、`from owlclaw.triggers`、`from owlclaw.capabilities` 的直接导入
- [ ] 10.2 实现集成测试：FastAPI TestClient + mock Provider 覆盖全部 API 端点
- [ ] 10.3 性能基准测试：核心 API P95 < 200ms

**验收**：
- 架构隔离扫描通过（CI 门禁）
- 集成测试覆盖全部 API 端点
- 性能基准满足 NFR-1
- `poetry run pytest tests/unit/web/ tests/integration/test_console_api.py` 全部通过

---

**维护者**：yeemio  
**最后更新**：2026-02-28
