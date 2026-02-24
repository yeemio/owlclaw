# Requirements Document: declarative-binding

## 文档联动

- requirements: `.kiro/specs/declarative-binding/requirements.md`
- design: `.kiro/specs/declarative-binding/design.md`
- tasks: `.kiro/specs/declarative-binding/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`
- architecture: `docs/ARCHITECTURE_ANALYSIS.md` §4.12

## Introduction

Declarative Binding（声明式工具绑定）是 OwlClaw 决策 4.12 的核心实现。它让 SKILL.md 从"知识文档"升级为"可执行契约"——业务开发者在 `metadata.json` 的 `binding` 字段中声明工具的接入方式（HTTP/Queue/SQL/gRPC），Agent 运行时根据声明自动完成调用，无需编写 Python `@handler` 适配代码。

这解决了 OwlClaw 当前最大的接入壁垒：存量系统（Java/Go/.NET 技术栈）必须编写 Python 适配代码才能被 Agent 调用。通过 Declarative Binding，一个 SKILL.md 文件同时描述"做什么"（业务知识）和"怎么连"（接入信息），实现真正的零代码接入。

### 业界参考

- **Dapr Bindings**：YAML 声明 binding 类型 + sidecar 代理执行（借鉴类型分类和 credential 引用模式）
- **MCP Tools**：JSON Schema 声明工具签名（借鉴 inputSchema 格式和工具发现协议）
- **Terraform Provider**：声明式资源管理 + Provider 注册机制（借鉴可扩展的注册架构）

### 与 FastPath 提案的关系

本 spec 取代 `docs/ZERO_CODE_FASTPATH_DECISION_PROPOSAL.md` 中的 HTTP Edge 和 LLM Proxy 方案。FastPath 的核心需求通过 binding + shadow 模式满足。

## Glossary

- **Binding**: 声明式工具绑定，描述工具如何连接到外部系统（HTTP endpoint、消息队列、数据库）
- **BindingTool**: 由 binding 声明自动生成的工具实例，无需 `@handler` 代码
- **Binding Executor**: 执行器，按 binding 类型（HTTP/Queue/SQL）实际执行调用
- **Shadow Mode**: 旁路模式，调用目标系统但不产生副作用，用于零代码对比验证
- **Active Mode**: 正常模式，调用目标系统并返回真实结果
- **Credential Reference**: 环境变量引用（`${VAR_NAME}`），用于在 binding 中引用敏感信息
- **Response Mapping**: 响应映射，从外部系统响应中提取有效数据
- **Parameter Mapping**: 参数映射，将工具参数绑定到 SQL 查询占位符

## Requirements

### Requirement 1: Binding Schema 定义

**User Story:** 作为 SKILL.md 作者，我希望在 metadata.json 中通过 `binding` 字段声明工具的接入方式，这样 Agent 可以自动调用外部系统而无需我编写 Python 代码。

#### Acceptance Criteria

1. THE binding field SHALL support four types: `http`, `queue`, `sql`, `grpc`
2. THE binding field SHALL be optional — tools without binding continue to require `@handler` registration
3. EACH binding type SHALL define type-specific fields (url/method for HTTP, topic/provider for Queue, query for SQL)
4. THE binding field SHALL support `mode` with values `active` (default) and `shadow`
5. THE binding field SHALL support `timeout_ms` (default 5000) and `retry` configuration
6. THE binding schema SHALL be validated by `owlclaw skill validate` command
7. THE binding field SHALL NOT contain plaintext credentials — all secrets must use `${ENV_VAR}` references
8. FOR ALL binding types, the schema SHALL be expressible as JSON Schema for cross-language validation

### Requirement 2: HTTP Binding Executor

**User Story:** 作为存量系统的接入者，我希望通过 HTTP binding 声明 REST API 的调用方式，这样 Agent 可以直接调用我的 Java/Go/.NET 服务。

#### Acceptance Criteria

1. THE HTTPBinding executor SHALL support methods: GET, POST, PUT, PATCH, DELETE
2. THE url field SHALL support path parameter templates (`{param_name}`) resolved from tool arguments
3. THE headers field SHALL support `${ENV_VAR}` references for credential injection
4. THE response_mapping SHALL extract data from response body using JSONPath-like syntax
5. THE response_mapping SHALL map HTTP status codes to semantic errors (success/not_found/rate_limited)
6. WHEN in shadow mode, write operations (POST/PUT/PATCH/DELETE) SHALL be logged to Ledger without execution
7. WHEN in shadow mode, read operations (GET) SHALL execute normally and return results
8. THE executor SHALL enforce timeout and retry policies from binding configuration
9. THE executor SHALL sanitize both request parameters and response data through security module

### Requirement 3: Queue Binding Executor

**User Story:** 作为消息驱动系统的接入者，我希望通过 Queue binding 声明消息发送方式，这样 Agent 可以向我的 Kafka/RabbitMQ 队列发送消息。

#### Acceptance Criteria

1. THE QueueBinding executor SHALL support providers: kafka, rabbitmq, redis
2. THE executor SHALL reuse existing `owlclaw/integrations/queue_adapters/` implementations
3. THE connection field SHALL use `${ENV_VAR}` references
4. THE headers_mapping SHALL inject tracing information (correlation_id, source)
5. WHEN in shadow mode, queue produce SHALL log message to Ledger without actual send
6. THE executor SHALL support `format` field for message serialization (json, avro, protobuf)
7. THE executor SHALL enforce timeout and retry policies

### Requirement 4: SQL Binding Executor

**User Story:** 作为数据分析场景的接入者，我希望通过 SQL binding 声明数据库查询，这样 Agent 可以直接查询我的业务数据库。

#### Acceptance Criteria

1. THE SQLBinding executor SHALL support parameterized queries only — string concatenation is FORBIDDEN
2. THE parameter_mapping SHALL bind tool arguments to SQL query placeholders (`:param`)
3. THE `read_only` field SHALL default to `true`; write operations require explicit `read_only: false`
4. WHEN `read_only: false`, THE executor SHALL require `risk_level: high` or above in SKILL.md
5. THE connection field SHALL use `${ENV_VAR}` references
6. THE executor SHALL enforce query timeout and result row limits
7. THE executor SHALL sanitize query results before returning to Agent

### Requirement 5: Binding Tool Registration

**User Story:** 作为 OwlClaw 运行时，我需要自动检测 SKILL.md 中的 binding 声明并注册为可调用工具，这样有 binding 的工具和有 @handler 的工具可以共存。

#### Acceptance Criteria

1. THE Skills loader SHALL detect `binding` field in tools_schema during scan
2. WHEN binding is present, THE loader SHALL auto-register a BindingTool (no `@handler` needed)
3. WHEN binding is absent, THE loader SHALL require traditional `@handler` registration (existing behavior)
4. THE BindingTool SHALL appear in capability registry alongside handler-registered tools
5. THE BindingTool SHALL be subject to governance visibility filtering, budget limits, and rate limiting
6. THE BindingTool SHALL record all invocations to Ledger (request params, response summary, latency, status)
7. WHEN both binding and @handler exist for the same tool, @handler SHALL take precedence

### Requirement 6: Credential Security

**User Story:** 作为安全工程师，我需要确保 binding 中的敏感信息不会泄露，这样 SKILL.md 可以安全地存储在版本控制中。

#### Acceptance Criteria

1. THE binding schema SHALL reject any field value that looks like a plaintext secret (heuristic detection)
2. ALL credential fields SHALL use `${ENV_VAR}` syntax, resolved at runtime from environment or owlclaw.config
3. THE `owlclaw skill validate` command SHALL warn when binding contains potential plaintext secrets
4. THE credential resolver SHALL support `.env` files, system environment variables, and owlclaw.yaml secrets section
5. WHEN an `${ENV_VAR}` reference cannot be resolved, THE executor SHALL fail with a clear error (not silently use empty string)

### Requirement 7: Shadow Mode for Zero-Code Comparison

**User Story:** 作为存量系统的评估者，我希望使用 shadow 模式观察 Agent 的行为而不影响生产系统，这样我可以在正式接入前验证 Agent 的决策质量。

#### Acceptance Criteria

1. WHEN `mode: shadow`, write operations SHALL be recorded to Ledger without actual execution
2. WHEN `mode: shadow`, read operations SHALL execute normally
3. THE shadow execution results SHALL be queryable through Ledger API
4. THE shadow results SHALL be compatible with `e2e-validation` report_generator for comparison reports
5. THE mode SHALL be switchable per-tool without code changes (only metadata.json modification)

### Requirement 8: Binding Executor Extensibility

**User Story:** 作为 OwlClaw 扩展开发者，我希望能注册自定义 binding 类型，这样我可以支持 gRPC、GraphQL 等协议。

#### Acceptance Criteria

1. THE binding executor registry SHALL support registration of custom executor types
2. THE custom executor SHALL implement a standard interface (execute, validate_config, supported_modes)
3. THE gRPC binding type SHALL be reserved but not implemented in MVP
4. THE executor registry SHALL raise clear errors for unknown binding types

### Requirement 9: Skill Prerequisites（加载前提条件）

**User Story:** 作为 Skill 作者，我希望声明 Skill 的运行前提条件（环境变量、CLI 工具、配置项），这样不满足条件的 Skill 不会被加载到 Agent prompt 中，避免 Agent 调用注定失败的工具。

#### Acceptance Criteria

1. THE `owlclaw.prerequisites` field SHALL support: `env` (环境变量列表)、`bins` (CLI 工具列表)、`config` (owlclaw.yaml 配置路径列表)、`python_packages` (Python 包列表)、`os` (操作系统列表)
2. WHEN prerequisites are not met, THE Skill SHALL be skipped during loading with a warning log
3. THE `owlclaw skill validate` command SHALL check prerequisites against current environment
4. THE prerequisites check SHALL run at load time (not at invocation time) to fail fast
5. ALL prerequisite fields SHALL be optional — a Skill with no prerequisites is always eligible

### Requirement 10: 简化 Tools 声明语法

**User Story:** 作为非技术背景的业务人员，我希望用简单的 YAML 语法声明工具参数，而不是写完整的 JSON Schema，这样我可以更快地创建 SKILL.md。

#### Acceptance Criteria

1. THE tools declaration SHALL support a simplified YAML syntax: `param_name: type` (e.g., `warehouse_id: string`)
2. THE runtime SHALL auto-expand simplified declarations to full JSON Schema
3. THE simplified syntax SHALL support: string, number, integer, boolean, array, object
4. THE simplified syntax SHALL support optional description via `param_name: { type: string, description: "..." }`
5. WHEN both simplified and full JSON Schema are provided, full JSON Schema SHALL take precedence
6. THE `owlclaw skill validate` command SHALL accept both formats

### Requirement 11: SKILL.md 最小可用规范

**User Story:** 作为第一次接触 OwlClaw 的开发者，我希望用最少的内容创建一个可工作的 SKILL.md，这样我可以在 5 分钟内上手。

#### Acceptance Criteria

1. A SKILL.md with only `name`, `description`, and a Markdown body SHALL be a valid, loadable Skill
2. ALL `owlclaw:` extension fields SHALL be optional with sensible defaults
3. ALL `metadata:` fields SHALL be optional
4. THE `owlclaw skill init` command SHALL have a "minimal" mode generating only name + description + body
5. THE default template generated by `owlclaw skill init` SHALL be the minimal version (not the full template)

### Requirement 12: cli-migrate 自动生成 Binding SKILL.md

**User Story:** 作为 IT 运维人员，我希望运行一条命令就能从已有系统的 OpenAPI 规范或 ORM 模型自动生成包含 Declarative Binding 的 SKILL.md，这样我不需要手写 JSON Schema 和 URL 模板。

#### Acceptance Criteria

1. WHEN 用户执行 `owlclaw migrate scan --openapi <spec_url> --output-mode binding`，THE CLI_Migrate SHALL 解析 OpenAPI 规范并为每个 API 端点生成包含 HTTP Binding 的 SKILL.md
2. THE generated SKILL.md SHALL include: name (from operationId/summary), description (from API description), tools_schema with binding (type=http, method, url template, headers, response_mapping), and prerequisites.env (from security schemes)
3. WHEN 用户执行 `owlclaw migrate scan --orm <models_path> --output-mode binding`，THE CLI_Migrate SHALL 识别 ORM 模型并为常见查询模式生成包含 SQL Binding 的 SKILL.md
4. THE generated SQL Binding SHALL use parameterized queries only, with `read_only: true` as default
5. THE `--output-mode` flag SHALL support values: `handler` (default, existing behavior), `binding` (new), `both` (generate both @handler code and binding SKILL.md)
6. THE generated SKILL.md SHALL pass `owlclaw skill validate` without errors
7. THE generated binding SHALL use `${ENV_VAR}` references for all credentials, with prerequisites.env listing required variables
8. THE generated SKILL.md body SHALL contain a placeholder for business rules, prompting the business user to fill in natural language descriptions

### Requirement 13: 三种用户角色的工作流

**User Story:** 作为 OwlClaw 的产品设计者，我需要确保三种用户角色（IT 运维、业务用户、AI 开发者）各自的工作流清晰且工作量最小化。

#### Acceptance Criteria

1. IT 运维的工作流 SHALL be: 运行 `owlclaw migrate scan` → 配置环境变量 → 完成（分钟级，一次性）
2. 业务用户的工作流 SHALL be: 用自然语言编写 SKILL.md body（业务规则、决策指引）→ 完成（分钟级，按需）
3. AI 开发者的工作量 SHALL be zero — Agent 自动理解 binding + 业务知识
4. THE documentation SHALL clearly describe these three roles and their workflows
5. THE `owlclaw skill init` command SHALL support a `--from-binding` mode that generates a minimal SKILL.md body template referencing existing binding tools

## Architecture Exception Statement

本 spec 无数据库铁律例外。Binding 执行器不直接操作 OwlClaw 内部数据库；SQL Binding 连接的是外部业务数据库，不受 OwlClaw 的 tenant_id / UUID 等铁律约束（那是业务系统自己的 schema）。

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-24
**优先级**: P0（MVP 核心能力）
**预估工作量**: 5-8 天
