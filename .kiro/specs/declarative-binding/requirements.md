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

## Architecture Exception Statement

本 spec 无数据库铁律例外。Binding 执行器不直接操作 OwlClaw 内部数据库；SQL Binding 连接的是外部业务数据库，不受 OwlClaw 的 tenant_id / UUID 等铁律约束（那是业务系统自己的 schema）。

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-24
**优先级**: P0（MVP 核心能力）
**预估工作量**: 5-8 天
