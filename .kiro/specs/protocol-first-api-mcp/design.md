# Design: Protocol-first API + MCP

> **目标**：构建 OwlClaw 的统一协议产品面（API + MCP），以 Gateway-first 方式服务跨语言接入。  
> **状态**：已完成（通过子 spec 实施与验收）  
> **最后更新**：2026-02-27

---

## 1. 架构设计

### 1.1 整体架构

```text
                    External Clients
        (Java / Go / .NET / Python / MCP Clients)
                              |
                              v
                  +-----------------------+
                  |  OwlClaw Gateway      |
                  |  (Protocol Surface)   |
                  +-----+-----------+-----+
                        |           |
                 HTTP API           MCP
            (OpenAPI Contract) (MCP Contract)
                        |           |
                        +-----+-----+
                              v
                    +-------------------+
                    | Protocol Core     |
                    | - version policy  |
                    | - error domain    |
                    | - authn/authz     |
                    | - compatibility   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | OwlClaw Runtime   |
                    | governance/triggers|
                    | skills/integrations|
                    +---------+---------+
                              |
                              v
                 +----------------------------+
                 | Ledger + Observability     |
                 | (trace/metrics/audit)      |
                 +----------------------------+
```

### 1.2 核心组件

#### 组件 1：Protocol Gateway

**职责**：统一承载 API 与 MCP 入口，执行版本协商、鉴权、路由和治理前置校验。

**接口定义**：

```python
class ProtocolGateway:
    async def route_http(self, request: HttpRequest) -> HttpResponse: ...
    async def route_mcp(self, request: McpMessage) -> McpMessage: ...
    async def negotiate_version(self, ctx: ProtocolContext) -> VersionDecision: ...
```

#### 组件 2：Protocol Policy Engine

**职责**：处理兼容性规则、错误码规范、弃用窗口、变更等级。

**接口定义**：

```python
class ProtocolPolicyEngine:
    def classify_change(self, before: Contract, after: Contract) -> ChangeLevel: ...
    def validate_compatibility(self, change: ChangeLevel) -> ValidationResult: ...
    def map_error(self, source_error: Exception) -> ProtocolError: ...
```

#### 组件 3：Contract Test Harness

**职责**：以契约测试和差异检测方式对 API/MCP 进行发布门禁。

**接口定义**：

```python
class ContractHarness:
    def run_api_contract_tests(self) -> TestReport: ...
    def run_mcp_contract_tests(self) -> TestReport: ...
    def run_breaking_diff(self) -> DiffReport: ...
```

---

## 2. 实现细节

### 2.1 文件结构

```text
.kiro/specs/protocol-first-api-mcp/
├── requirements.md
├── design.md
└── tasks.md

docs/protocol/
├── VERSIONING.md
├── ERROR_MODEL.md
├── COMPATIBILITY_POLICY.md
└── JAVA_GOLDEN_PATH.md

tests/contracts/
├── api/
└── mcp/
```

### 2.2 协议版本策略实现

**当前问题**：版本策略分散，缺少统一兼容门禁。

**解决方案**：

- API 使用显式版本规则（header 或 path，按 release policy 统一）。
- MCP 使用 initialize 协商结果绑定能力面版本。
- 统一定义 change level：`compatible / additive / breaking`。

**关键点**：

- 版本策略必须是可执行规则，不是纯说明文字。
- breaking 变更需满足迁移窗口与回滚方案。

### 2.3 错误语义统一

**当前问题**：API 与 MCP 错误语义在字段层面不完全一致。

**解决方案**：

- API 错误采用 Problem Details 基线字段。
- MCP 错误码与 API 错误域做映射表（包括 `retryable`、`category`、`incident_id`）。

**关键点**：

- 客户端需可仅凭 machine-readable 字段判断是否重试。
- 错误日志字段与审计字段保持一致，便于关联追踪。

### 2.4 Java Golden Path

**当前问题**：跨语言接入缺少可复制范式。

**解决方案**：

- 定义 Java 最小接入样板（触发、查询、错误处理三步）。
- 输出请求签名、超时、重试、幂等示例。

**关键点**：

- 验收要求“可运行证据”，避免只产文档。

---

## 3. 数据流

### 3.1 API 调用流程（触发）

```text
Java Client
   |
   | POST /v1/agent/trigger
   v
Protocol Gateway
   |
   | version + auth + schema validation
   v
Runtime Trigger Entry
   |
   | governance checks + execution
   v
Ledger/Trace
   |
   v
HTTP Response (problem/details on failure)
```

### 3.2 MCP 调用流程（工具调用）

```text
MCP Client
   |
   | initialize -> tools/list -> tools/call
   v
MCP Gateway Adapter
   |
   | capability negotiation + policy checks
   v
Tool Execution + Governance
   |
   v
Ledger/Trace + MCP Result
```

---

## 4. 错误处理

### 4.1 兼容性违规

**场景**：提交引入 breaking 协议变更，但未提供迁移窗口。

**处理**：

- CI 契约门禁阻断。
- 生成差异报告并标注阻断原因。

### 4.2 版本协商失败

**场景**：客户端请求不受支持的协议版本。

**处理**：

- API 返回版本不兼容错误（含支持范围）。
- MCP 返回协商失败响应并给出可升级路径。

### 4.3 治理拒绝

**场景**：调用触发预算/限流/权限拒绝。

**处理**：

- 统一错误域返回。
- 明确 `retryable`、`retry_after` 与 trace id。

---

## 5. 配置

### 5.1 配置文件

```yaml
protocol:
  api:
    version_mode: header
    default_version: v1
  mcp:
    supported_versions: ["2025-06", "2025-03"]
  compatibility:
    block_breaking_without_migration: true
  error:
    include_incident_id: true
```

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OWLCLAW_PROTOCOL_DEFAULT_API_VERSION` | API 默认版本 | `v1` |
| `OWLCLAW_PROTOCOL_MCP_VERSIONS` | MCP 支持版本列表 | `2025-06,2025-03` |
| `OWLCLAW_PROTOCOL_BLOCK_BREAKING` | 是否阻断 breaking 变更 | `true` |

---

## 6. 测试策略

### 6.1 单元测试

- 版本协商决策逻辑。
- 错误映射逻辑。
- 兼容性分级判断逻辑。

### 6.2 集成测试

- API 端到端契约调用（包含错误场景）。
- MCP 端到端协议调用（initialize/list/call/read）。

### 6.3 契约门禁测试

- API 契约差异检测（breaking/additive 分类）。
- MCP 协议能力回归（方法可用、字段完整、错误语义稳定）。

### 6.4 跨语言验证

- Java/curl 样例脚本可执行并校验输出字段。

---

## 7. 迁移计划

### 7.1 Phase 1：协议宪法（2-3 天）

- 版本策略、兼容策略、错误模型文档化。
- 契约差异门禁接入 CI（先警告、后阻断）。

### 7.2 Phase 2：最小协议面（3-5 天）

- API 三端点契约与回归。
- MCP 核心路径契约与回归。

### 7.3 Phase 3：跨语言与运维（3-5 天）

- Java Golden Path 完整验证。
- 发布门控（canary/rollback）与操作手册补齐。

---

## 8. 风险与缓解

### 8.1 风险：团队短期感知研发速度下降

**影响**：对协议治理价值缺乏即时反馈。

**缓解**：

- 通过自动化门禁替代人工审查，长期净效率上升。
- 先做高频接口，避免过度治理。

### 8.2 风险：双协议面出现语义漂移

**影响**：API 与 MCP 返回不一致，增加客户端复杂度。

**缓解**：

- 强制统一错误域与审计字段。
- 引入 API/MCP 对齐矩阵作为评审硬门槛。

---

## 9. 契约与 Mock

### 9.1 API 契约

- 使用 OpenAPI 维护请求/响应 schema。
- 错误采用 Problem Details。

### 9.2 MCP 契约

- 使用 MCP initialize/tools/resources 最小路径作为基线契约。
- 错误码与重试语义与 API 对齐映射。

### 9.3 Mock 策略

- 协议测试默认使用 in-memory/mock runtime，不依赖生产外部服务。
- 仅发布前回归触发真实依赖验收。

---

## 10. 红军视角自审

### 10.1 攻击面 1：协议治理过重导致业务交付变慢

**反证**：若每次变更都需复杂评审，可能压垮小团队节奏。

**防御策略**：

- 分层治理：高风险接口强门禁，低风险文档变更轻门禁。
- 引入“快速通道”但保留追溯证据。

### 10.2 攻击面 2：MCP 与 API 双栈维护成本翻倍

**反证**：两个入口分别实现会长期分叉。

**防御策略**：

- 单一 Gateway 核心，协议适配层复用同一执行链路。
- 统一审计与错误域，防止语义重复实现。

### 10.3 攻击面 3：跨语言样例沦为演示，不可生产

**反证**：示例代码通常无法覆盖真实重试、幂等、鉴权场景。

**防御策略**：

- 验收改为“可执行脚本 + 实际返回校验”。
- 将 Java 样例纳入回归（至少 nightly）。

### 10.4 攻击面 4：安全项只停留文档

**反证**：若无默认策略与检测，协议入口成为新攻击面。

**防御策略**：

- 默认拒绝策略、最小权限、来源限制、失败审计入 CI 检查项。
- 安全配置缺失时阻断发布。

---

## 11. 参考文档

- `docs/ARCHITECTURE_ANALYSIS.md`（决策 4.11）
- `.kiro/specs/mcp-server/design.md`
- `.kiro/specs/triggers-api/design.md`
- `.kiro/specs/test-infra/design.md`

---

## 12. 实施映射

- 协议治理与错误模型：`protocol-governance`（27/27）
- API/MCP 契约门禁：`contract-testing`（19/19）
- 网关发布与运维：`gateway-runtime-ops`（18/18）
- 跨语言接入路径：`cross-lang-golden-path`（16/16）
- 发布供应链安全（外部依赖项）：`release-supply-chain`（9/15，继续推进）

**维护者**：OwlClaw 架构组  
**最后更新**：2026-02-27
