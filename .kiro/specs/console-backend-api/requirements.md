# Requirements: Console Backend API

> **目标**：为 OwlClaw Web Console 提供 REST API 后端，作为治理控制面的数据层  
> **优先级**：P0  
> **预估工作量**：8-12 天

---

## 1. 背景与动机

### 1.1 当前问题

OwlClaw 已完成 Agent 运行时、治理层、触发器、Skills 生态等核心模块，但缺少统一的可视化入口。运维人员需要通过 CLI、日志、Langfuse Dashboard、Hatchet UI 等多个工具分散查看系统状态，无法一眼掌握全局。

### 1.2 设计目标

提供一组 REST API，将 OwlClaw 各模块的运行时数据聚合输出，供 Console 前端 SPA 消费。API 层通过查询契约（Protocol 接口）与底层模块解耦，确保底层 Spec 变更不会直接波及 API 层。

---

## 2. 用户故事

### 2.1 作为运维人员

**故事 1**：系统全局概览
```
作为运维人员
我希望通过一个 API 获取系统健康状态和关键指标
这样我可以在 Console 首页一眼判断系统是否正常
```

**验收标准**：
- [ ] GET /api/v1/overview 返回 Runtime/DB/Hatchet/LLM/Langfuse 连通性
- [ ] 返回今日成本、执行次数、成功率、活跃 Agent 数

**故事 2**：治理数据查看
```
作为运维人员
我希望通过 API 查看预算消耗、限流熔断状态、能力可见性矩阵
这样我可以监控治理策略的执行效果
```

**验收标准**：
- [ ] GET /api/v1/governance/budget 返回预算消耗趋势
- [ ] GET /api/v1/governance/circuit-breakers 返回熔断器状态
- [ ] GET /api/v1/governance/visibility-matrix 返回能力可见性矩阵

**故事 3**：执行审计
```
作为运维人员
我希望通过 API 查询执行记录并按多维度筛选
这样我可以追溯任意一次 Agent 决策的完整链路
```

**验收标准**：
- [ ] GET /api/v1/ledger 支持 agent_id/capability/时间/成本/状态筛选
- [ ] 支持分页（offset/limit）和排序
- [ ] 返回详情包含输入参数、输出结果、决策推理、模型、token 用量

**故事 4**：触发器监控
```
作为运维人员
我希望通过 API 查看所有触发器的状态和执行历史
这样我可以确认事件驱动链路正常运行
```

**验收标准**：
- [ ] GET /api/v1/triggers 返回 6 类触发器的统一状态
- [ ] 每个触发器包含启用状态、下次触发时间、成功率

### 2.2 作为开发者

**故事 5**：能力注册查看
```
作为开发者
我希望通过 API 查看已注册的 Handlers、Skills、Bindings
这样我可以确认业务能力是否正确加载
```

**验收标准**：
- [ ] GET /api/v1/capabilities 返回分类列表（handler/skill/binding）
- [ ] 每个能力包含 JSON Schema、约束条件、调用统计

**故事 6**：配置与诊断
```
作为开发者
我希望通过 API 查看运行时配置和系统信息
这样我可以诊断配置问题
```

**验收标准**：
- [ ] GET /api/v1/settings 返回运行时配置（脱敏）
- [ ] 返回 MCP Server 状态、DB 迁移版本、系统版本信息

---

## 3. 功能需求

### 3.1 API 框架

#### FR-1：REST API 路由挂载

**需求**：基于 FastAPI/Starlette 实现 REST API，挂载到 `/api/v1/` 前缀。

**验收标准**：
- [ ] API 路由可挂载到现有 OwlClaw 应用的同一端口
- [ ] 支持 CORS 配置
- [ ] 自动生成 OpenAPI Schema（`/api/v1/openapi.json`）

#### FR-2：认证中间件

**需求**：实现 Token 认证中间件（MVP 阶段使用静态 Token）。

**验收标准**：
- [ ] 无 Token 请求返回 401
- [ ] Token 通过环境变量 `OWLCLAW_CONSOLE_TOKEN` 配置
- [ ] 可通过配置禁用认证（开发模式）

#### FR-3：通用分页与筛选

**需求**：提供统一的分页、筛选、排序框架。

**验收标准**：
- [ ] 所有列表 API 支持 `offset`/`limit` 分页
- [ ] 筛选参数通过 Query Parameters 传递
- [ ] 返回格式统一：`{ items: [...], total: N, offset: M, limit: L }`

#### FR-4：错误处理

**需求**：统一的错误响应格式。

**验收标准**：
- [ ] 错误响应格式：`{ error: { code: "...", message: "...", details: {...} } }`
- [ ] 4xx/5xx 错误均遵循统一格式
- [ ] 底层异常不泄漏到 API 响应

### 3.2 数据 API

#### FR-5：Overview API

**需求**：系统健康和关键指标聚合。

**验收标准**：
- [ ] 返回各组件连通性（Runtime/DB/Hatchet/LLM/Langfuse）
- [ ] 返回今日关键指标（成本/执行次数/成功率/活跃 Agent）
- [ ] 告警规则可配置（成本超阈值、成功率低于阈值）

#### FR-6：Agents API

**需求**：Agent 列表和详情。

**验收标准**：
- [ ] 返回 Agent 列表（身份配置、记忆统计、知识库挂载）
- [ ] 返回单个 Agent 的运行历史（Ledger 聚合）

#### FR-7：Governance API

**需求**：治理数据聚合。

**验收标准**：
- [ ] 预算消耗趋势（按天/周/月聚合）
- [ ] 限流/熔断状态实时查询
- [ ] 能力可见性矩阵（Agent × Capability）
- [ ] migration_weight 进度
- [ ] Skills 质量评分排行

#### FR-8：Capabilities API

**需求**：能力注册信息。

**验收标准**：
- [ ] Handlers/Skills/Bindings 分类列表
- [ ] JSON Schema 查看
- [ ] 调用统计（从 Ledger 聚合）
- [ ] cli-scan 扫描结果视图
- [ ] cli-migrate 迁移进度视图

#### FR-9：Triggers API

**需求**：触发器统一状态。

**验收标准**：
- [ ] 6 类触发器统一状态聚合（cron/webhook/queue/db_change/api/signal）
- [ ] 执行历史查询
- [ ] 下次触发时间

#### FR-10：Ledger API

**需求**：执行审计数据。

**验收标准**：
- [ ] 多维筛选（Agent/Capability/时间/成本/状态）
- [ ] 分页与排序
- [ ] 详情展开（输入/输出/成本/模型/延迟/决策推理）

#### FR-11：Settings API

**需求**：运行时配置和系统信息。

**验收标准**：
- [ ] 运行时配置（只读，敏感字段脱敏）
- [ ] MCP Server 状态和已连接客户端
- [ ] DB 迁移版本
- [ ] 版本号/构建时间/commit hash
- [ ] OwlHub 连接状态

### 3.3 实时推送

#### FR-12：WebSocket 实时流

**需求**：关键指标和事件的实时推送。

**验收标准**：
- [ ] WebSocket 端点 `/api/v1/ws`
- [ ] 推送 Overview 指标变化
- [ ] 推送 Trigger 事件
- [ ] 推送 Ledger 新记录

---

## 4. 非功能需求

### 4.1 性能

**NFR-1：API 响应延迟**
- 列表 API P95 < 200ms（1000 条以内）
- 聚合 API P95 < 500ms

**验收标准**：
- [ ] 基准测试覆盖核心 API 端点

### 4.2 安全

**NFR-2：数据脱敏**
- API 密钥、数据库密码等敏感配置不得出现在 API 响应中

**验收标准**：
- [ ] Settings API 对敏感字段自动脱敏
- [ ] 测试验证无敏感数据泄漏

### 4.3 架构隔离

**NFR-3：查询契约层隔离**
- Console REST API 禁止直接 import 底层模块，必须通过 Protocol 接口

**验收标准**：
- [ ] `owlclaw/web/api/` 中无 `from owlclaw.agent` / `from owlclaw.governance` / `from owlclaw.triggers` / `from owlclaw.capabilities` 的直接导入
- [ ] 所有数据访问通过 `owlclaw/web/contracts.py` 定义的 Protocol

---

## 5. 验收标准总览

### 5.1 功能验收
- [ ] **FR-1**：API 路由挂载，OpenAPI Schema 可访问
- [ ] **FR-2**：Token 认证生效
- [ ] **FR-3**：分页/筛选框架统一
- [ ] **FR-4**：错误响应格式统一
- [ ] **FR-5~FR-11**：7 个数据 API 均返回正确数据
- [ ] **FR-12**：WebSocket 实时推送可连接

### 5.2 非功能验收
- [ ] **NFR-1**：核心 API P95 < 200ms
- [ ] **NFR-2**：敏感数据脱敏
- [ ] **NFR-3**：架构隔离（无直接底层导入）

### 5.3 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖核心 API 端点
- [ ] 架构隔离自动检测（import 扫描）

---

## 6. 约束与假设

### 6.1 约束
- MVP 阶段只读，不提供写入 API
- 认证使用静态 Token，RBAC 留企业版
- 必须使用查询契约层（Protocol），不得直接耦合底层模块

### 6.2 假设
- FastAPI 和 Starlette 已是项目依赖
- 底层模块的数据查询接口已稳定（Phase 1-8 已完成）
- Console 前端和后端在同一进程运行（同端口）

---

## 7. 依赖

### 7.1 外部依赖
- FastAPI（已有）
- Starlette（已有）
- uvicorn（已有）

### 7.2 内部依赖
- `owlclaw.governance.ledger` — Ledger 数据查询
- `owlclaw.capabilities.registry` — 能力注册信息
- `owlclaw.governance.visibility` — 可见性过滤
- `owlclaw.governance.router` — 模型路由配置
- `owlclaw.triggers.*` — 触发器状态
- `owlclaw.config` — 运行时配置
- `owlclaw.agent` — Agent 运行时状态

---

## 8. 风险与缓解

### 8.1 风险：底层模块接口变更

**影响**：底层 Spec 修改可能导致 Console API 数据不一致

**缓解**：
- 查询契约层（Protocol）隔离，变更只影响 Provider 适配层
- `[console-impact]` 标注规则确保变更可追踪
- OpenAPI Schema 自动生成前端类型

### 8.2 风险：性能瓶颈

**影响**：聚合查询可能导致 API 响应慢

**缓解**：
- Overview 指标使用缓存（TTL 30s）
- Ledger 查询利用已有数据库索引
- 分页限制默认 50 条

---

## 9. Definition of Done

### 9.1 API 框架
- [ ] FastAPI 路由挂载到 `/api/v1/`，OpenAPI Schema 可访问
- [ ] Token 认证中间件生效（401 无 Token / 200 有 Token）
- [ ] 统一分页/筛选/错误响应格式

### 9.2 数据 API
- [ ] 7 个数据 API（Overview/Agents/Governance/Capabilities/Triggers/Ledger/Settings）均返回结构化数据
- [ ] WebSocket 端点可连接并接收推送

### 9.3 架构隔离
- [ ] `owlclaw/web/api/` 无底层模块直接导入（自动化扫描验证）
- [ ] 所有数据通过 Protocol 接口获取

### 9.4 验收矩阵

| API 端点 | 返回正确数据 | 分页/筛选 | 错误处理 | 脱敏 | 测试 |
|----------|------------|----------|---------|------|------|
| Overview | [ ] | N/A | [ ] | [ ] | [ ] |
| Agents | [ ] | [ ] | [ ] | N/A | [ ] |
| Governance | [ ] | [ ] | [ ] | N/A | [ ] |
| Capabilities | [ ] | [ ] | [ ] | N/A | [ ] |
| Triggers | [ ] | [ ] | [ ] | N/A | [ ] |
| Ledger | [ ] | [ ] | [ ] | N/A | [ ] |
| Settings | [ ] | N/A | [ ] | [ ] | [ ] |
| WebSocket | [ ] | N/A | [ ] | N/A | [ ] |

---

## 10. 参考文档

- `docs/ARCHITECTURE_ANALYSIS.md` §4.15 — Web Console 决策与隔离架构
- `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D15 — Web Console 架构决策
- `.cursor/rules/owlclaw_architecture.mdc` — Console 隔离约束
- `.cursor/rules/owlclaw_development.mdc` §七 — Console 影响评估规则
- `owlclaw/mcp/governance_tools.py` — Protocol 解耦参考实现

---

**维护者**：yeemio  
**最后更新**：2026-02-28
