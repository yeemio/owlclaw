# 设计文档：Webhook 触发器系统

## 概述

Webhook 触发器系统是 OwlClaw Agent 平台的关键组件，负责接收外部 HTTP 请求并触发代理执行。系统采用事件驱动架构，提供高可用性、安全性和可扩展性。

核心设计目标：
- **安全性**：多层认证和授权机制
- **可靠性**：幂等性保证和自动重试
- **可观测性**：完整的事件日志和监控指标
- **灵活性**：可配置的转换规则和执行模式
- **集成性**：与 Agent Runtime 和 Governance Layer 无缝集成

## 架构

系统采用分层架构，主要包含以下层次：

```
┌─────────────────────────────────────────────────────────┐
│                    外部系统                              │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/HTTPS
                      ▼
┌─────────────────────────────────────────────────────────┐
│              HTTP 接入层 (API Gateway)                   │
│  - 路由管理                                              │
│  - TLS 终止                                              │
│  - 速率限制                                              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              验证层 (Validation Layer)                   │
│  - 认证验证                                              │
│  - 签名验证                                              │
│  - 请求验证                                              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│            转换层 (Transformation Layer)                 │
│  - 负载解析                                              │
│  - 数据转换                                              │
│  - 模式验证                                              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│            执行层 (Execution Layer)                      │
│  - 幂等性检查                                            │
│  - 代理触发                                              │
│  - 响应处理                                              │
└─────────┬───────────────────────┬───────────────────────┘
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│  Agent Runtime   │    │  Governance Layer    │
│  - 代理执行      │    │  - 权限验证          │
│  - 状态管理      │    │  - 策略执行          │
└──────────────────┘    └──────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│            持久化层 (Persistence Layer)                  │
│  - 端点配置存储                                          │
│  - 事件日志存储                                          │
│  - 幂等性键存储                                          │
└─────────────────────────────────────────────────────────┘
```

### 关键设计决策

1. **异步优先**：默认采用异步执行模式，立即返回执行 ID，避免长时间阻塞 HTTP 连接
2. **幂等性保证**：使用幂等性键（Idempotency Key）防止重复执行
3. **事件溯源**：记录所有事件以支持审计和调试
4. **插件化转换**：支持自定义转换规则，适应不同的外部系统格式
5. **治理集成**：所有执行请求都经过治理层验证，确保合规性

## 组件和接口

### 1. WebhookEndpointManager

负责 Webhook 端点的生命周期管理。

```typescript
interface WebhookEndpointManager {
  // 创建新端点
  createEndpoint(config: EndpointConfig): Promise<WebhookEndpoint>
  
  // 获取端点配置
  getEndpoint(endpointId: string): Promise<WebhookEndpoint | null>
  
  // 更新端点配置
  updateEndpoint(endpointId: string, config: Partial<EndpointConfig>): Promise<WebhookEndpoint>
  
  // 删除端点
  deleteEndpoint(endpointId: string): Promise<void>
  
  // 列出所有端点
  listEndpoints(filter?: EndpointFilter): Promise<WebhookEndpoint[]>
  
  // 验证端点是否存在且活跃
  validateEndpoint(endpointId: string): Promise<boolean>
}

interface EndpointConfig {
  name: string
  targetAgentId: string
  authMethod: AuthMethod
  transformationRuleId?: string
  executionMode: 'sync' | 'async'
  timeout?: number
  retryPolicy?: RetryPolicy
  enabled: boolean
}

interface WebhookEndpoint {
  id: string
  url: string
  authToken: string
  config: EndpointConfig
  createdAt: Date
  updatedAt: Date
}
```

### 2. RequestValidator

负责验证传入的 HTTP 请求。

```typescript
interface RequestValidator {
  // 验证认证令牌
  validateAuth(request: HttpRequest, endpoint: WebhookEndpoint): Promise<ValidationResult>
  
  // 验证请求签名
  validateSignature(request: HttpRequest, secret: string): Promise<ValidationResult>
  
  // 验证请求格式
  validateFormat(request: HttpRequest): Promise<ValidationResult>
}

interface ValidationResult {
  valid: boolean
  error?: ValidationError
}

interface ValidationError {
  code: string
  message: string
  details?: Record<string, any>
}

type AuthMethod = 
  | { type: 'bearer'; token: string }
  | { type: 'hmac'; secret: string; algorithm: 'sha256' | 'sha512' }
  | { type: 'basic'; username: string; password: string }
```

### 3. PayloadTransformer

负责解析和转换 Webhook 负载。

```typescript
interface PayloadTransformer {
  // 解析负载
  parse(request: HttpRequest): Promise<ParsedPayload>
  
  // 应用转换规则
  transform(payload: ParsedPayload, rule: TransformationRule): Promise<AgentInput>
  
  // 验证转换后的数据
  validate(input: AgentInput, schema: Schema): Promise<ValidationResult>
}

interface ParsedPayload {
  contentType: string
  data: Record<string, any>
  headers: Record<string, string>
  rawBody: string
}

interface TransformationRule {
  id: string
  name: string
  sourceSchema?: Schema
  targetSchema: Schema
  mappings: FieldMapping[]
  customLogic?: string  // JavaScript 表达式
}

interface FieldMapping {
  source: string  // JSONPath 表达式
  target: string
  transform?: 'string' | 'number' | 'boolean' | 'date' | 'json'
  defaultValue?: any
}

interface AgentInput {
  agentId: string
  parameters: Record<string, any>
  context: ExecutionContext
}
```

### 4. ExecutionTrigger

负责触发代理执行。

```typescript
interface ExecutionTrigger {
  // 触发代理执行
  trigger(input: AgentInput, options: ExecutionOptions): Promise<ExecutionResult>
  
  // 检查幂等性
  checkIdempotency(key: string): Promise<ExecutionResult | null>
  
  // 记录幂等性键
  recordIdempotency(key: string, result: ExecutionResult, ttl: number): Promise<void>
  
  // 查询执行状态
  getExecutionStatus(executionId: string): Promise<ExecutionStatus>
}

interface ExecutionOptions {
  mode: 'sync' | 'async'
  timeout?: number
  idempotencyKey?: string
  retryPolicy?: RetryPolicy
}

interface ExecutionResult {
  executionId: string
  status: 'accepted' | 'running' | 'completed' | 'failed'
  startedAt: Date
  completedAt?: Date
  output?: any
  error?: ExecutionError
}

interface RetryPolicy {
  maxAttempts: number
  initialDelay: number  // 毫秒
  maxDelay: number
  backoffMultiplier: number
}
```

### 5. EventLogger

负责记录所有 Webhook 事件。

```typescript
interface EventLogger {
  // 记录请求事件
  logRequest(event: RequestEvent): Promise<void>
  
  // 记录验证事件
  logValidation(event: ValidationEvent): Promise<void>
  
  // 记录转换事件
  logTransformation(event: TransformationEvent): Promise<void>
  
  // 记录执行事件
  logExecution(event: ExecutionEvent): Promise<void>
  
  // 查询事件日志
  queryEvents(filter: EventFilter): Promise<WebhookEvent[]>
}

interface WebhookEvent {
  id: string
  timestamp: Date
  endpointId: string
  type: 'request' | 'validation' | 'transformation' | 'execution'
  data: Record<string, any>
  metadata: EventMetadata
}

interface EventMetadata {
  sourceIp: string
  userAgent?: string
  requestId: string
  duration?: number
}
```

### 6. MonitoringService

负责监控和告警。

```typescript
interface MonitoringService {
  // 记录指标
  recordMetric(metric: Metric): Promise<void>
  
  // 获取健康状态
  getHealthStatus(): Promise<HealthStatus>
  
  // 获取指标统计
  getMetrics(filter: MetricFilter): Promise<MetricStats>
  
  // 触发告警
  triggerAlert(alert: Alert): Promise<void>
}

interface Metric {
  name: string
  value: number
  timestamp: Date
  tags: Record<string, string>
}

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: HealthCheck[]
  timestamp: Date
}

interface HealthCheck {
  name: string
  status: 'pass' | 'fail'
  message?: string
}

interface MetricStats {
  requestCount: number
  successRate: number
  failureRate: number
  avgResponseTime: number
  p95ResponseTime: number
  p99ResponseTime: number
}
```

### 7. GovernanceClient

与治理层集成的客户端。

```typescript
interface GovernanceClient {
  // 验证执行权限
  checkPermission(request: PermissionRequest): Promise<PermissionResult>
  
  // 应用速率限制
  checkRateLimit(resource: string, identifier: string): Promise<RateLimitResult>
  
  // 记录审计日志
  auditLog(event: AuditEvent): Promise<void>
}

interface PermissionRequest {
  agentId: string
  userId?: string
  source: string
  context: ExecutionContext
}

interface PermissionResult {
  allowed: boolean
  reason?: string
  policies: string[]
}

interface RateLimitResult {
  allowed: boolean
  limit: number
  remaining: number
  resetAt: Date
}
```

## 数据模型

### 端点配置表 (webhook_endpoints)

```sql
CREATE TABLE webhook_endpoints (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  auth_token VARCHAR(255) NOT NULL,
  target_agent_id VARCHAR(64) NOT NULL,
  auth_method JSONB NOT NULL,
  transformation_rule_id VARCHAR(64),
  execution_mode VARCHAR(10) NOT NULL DEFAULT 'async',
  timeout INTEGER,
  retry_policy JSONB,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by VARCHAR(64),
  
  INDEX idx_target_agent (target_agent_id),
  INDEX idx_enabled (enabled)
);
```

### 事件日志表 (webhook_events)

```sql
CREATE TABLE webhook_events (
  id VARCHAR(64) PRIMARY KEY,
  endpoint_id VARCHAR(64) NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  source_ip VARCHAR(45),
  user_agent TEXT,
  request_id VARCHAR(64) NOT NULL,
  duration INTEGER,
  status VARCHAR(20),
  data JSONB,
  error JSONB,
  
  INDEX idx_endpoint_timestamp (endpoint_id, timestamp DESC),
  INDEX idx_request_id (request_id),
  INDEX idx_timestamp (timestamp DESC)
);
```

### 幂等性键表 (idempotency_keys)

```sql
CREATE TABLE idempotency_keys (
  key VARCHAR(255) PRIMARY KEY,
  endpoint_id VARCHAR(64) NOT NULL,
  execution_id VARCHAR(64) NOT NULL,
  result JSONB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  
  INDEX idx_endpoint (endpoint_id),
  INDEX idx_expires (expires_at)
);
```

### 转换规则表 (transformation_rules)

```sql
CREATE TABLE transformation_rules (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  source_schema JSONB,
  target_schema JSONB NOT NULL,
  mappings JSONB NOT NULL,
  custom_logic TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  
  INDEX idx_name (name)
);
```

### 执行记录表 (webhook_executions)

```sql
CREATE TABLE webhook_executions (
  id VARCHAR(64) PRIMARY KEY,
  endpoint_id VARCHAR(64) NOT NULL,
  agent_id VARCHAR(64) NOT NULL,
  request_id VARCHAR(64) NOT NULL,
  idempotency_key VARCHAR(255),
  status VARCHAR(20) NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  input JSONB,
  output JSONB,
  error JSONB,
  retry_count INTEGER DEFAULT 0,
  
  INDEX idx_endpoint_started (endpoint_id, started_at DESC),
  INDEX idx_agent_started (agent_id, started_at DESC),
  INDEX idx_status (status),
  INDEX idx_idempotency (idempotency_key)
);
```

## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*


### 属性 1：端点创建生成唯一标识和完整配置

*对于任何*端点配置，创建端点时应该生成唯一的端点 ID、URL 和认证令牌，并且所有配置字段（目标代理、认证方式、转换规则、执行模式）都应该被正确保存。

**验证需求：1.1, 1.2**

### 属性 2：端点查询返回所有已注册端点

*对于任何*端点集合，查询端点列表应该返回所有已创建且未删除的端点，且每个端点包含完整的配置信息。

**验证需求：1.3**

### 属性 3：端点更新验证和持久化

*对于任何*有效的配置更新，更新端点应该验证配置的有效性，保存更改，并且后续查询应该返回更新后的配置。无效配置应该被拒绝。

**验证需求：1.4, 10.3**

### 属性 4：端点删除后不可访问

*对于任何*已删除的端点，向该端点发送请求应该返回 404 错误，且该端点不应该出现在端点列表中。

**验证需求：1.5**

### 属性 5：认证令牌验证和错误响应

*对于任何*请求，如果认证令牌有效则通过验证，如果令牌无效或缺失则返回 401 错误。

**验证需求：2.1, 2.3**

### 属性 6：签名验证和错误响应

*对于任何*包含签名的请求，如果签名使用正确的密钥和算法计算则验证通过，如果签名验证失败则返回 403 错误。

**验证需求：2.2, 2.4**

### 属性 7：未知端点返回 404

*对于任何*不存在的端点 ID，向该端点发送请求应该返回 404 错误。

**验证需求：2.5**

### 属性 8：负载解析正确性

*对于任何*有效的 JSON、XML 或 form-urlencoded 格式的负载，解析应该将数据正确转换为结构化对象，且解析后的数据应该保留原始数据的所有信息。

**验证需求：3.1, 3.2, 3.3**

### 属性 9：转换规则应用正确性

*对于任何*解析后的负载和转换规则，应用转换应该根据字段映射和转换函数生成符合目标模式的代理输入，且所有映射的字段都应该被正确转换。

**验证需求：3.4**

### 属性 10：负载解析失败返回 400

*对于任何*无效格式的负载，解析失败应该返回 400 错误，且错误响应应该包含描述性的错误信息。

**验证需求：3.5**

### 属性 11：验证通过后触发代理执行

*对于任何*验证通过且转换完成的请求，系统应该调用 Agent_Runtime 执行指定的代理，并传递转换后的输入数据和执行上下文。

**验证需求：4.1, 4.2**

### 属性 12：执行启动返回执行信息

*对于任何*成功启动的代理执行，响应应该包含唯一的执行 ID、初始状态和时间戳。

**验证需求：4.3, 5.3**

### 属性 13：治理层拒绝返回 403

*对于任何*被治理层拒绝的执行请求，系统应该返回 403 错误，且错误响应应该包含拒绝原因。

**验证需求：4.4, 8.3**

### 属性 14：运行时不可用返回 503

*对于任何*Agent_Runtime 不可用的情况，系统应该返回 503 错误。

**验证需求：4.5**

### 属性 15：成功启动返回 202

*对于任何*成功启动的异步执行，系统应该返回 202 状态码和执行详情（包括执行 ID、状态、时间戳）。

**验证需求：5.1**

### 属性 16：错误处理返回适当状态码

*对于任何*请求处理失败的情况，系统应该返回适当的 HTTP 错误状态码（400/401/403/404/503）和包含错误类型、消息的错误详情。

**验证需求：5.2**

### 属性 17：同步模式等待完成

*对于任何*配置为同步执行模式的端点，请求应该等待代理执行完成后返回最终结果和输出数据。

**验证需求：5.4**

### 属性 18：异步模式立即返回

*对于任何*配置为异步执行模式的端点，请求应该在代理执行启动后立即返回执行 ID，而不等待执行完成。

**验证需求：5.5**

### 属性 19：请求处理完整日志

*对于任何*接收到的请求，系统应该记录请求信息（时间戳、来源 IP、端点 ID、请求头）、验证结果、转换过程和执行状态。

**验证需求：6.1, 6.2**

### 属性 20：执行完成日志

*对于任何*完成的代理执行，系统应该记录执行结果、耗时和资源使用情况。

**验证需求：6.3**

### 属性 21：错误日志详细信息

*对于任何*发生的错误，系统应该记录错误类型、错误消息和堆栈跟踪。

**验证需求：6.4**

### 属性 22：事件日志持久化往返

*对于任何*记录的事件日志，将日志写入存储后查询应该能够检索到相同的日志数据。

**验证需求：6.5**

### 属性 23：监控指标记录

*对于任何*处理的请求，系统应该更新监控指标（请求计数、成功率、失败率、响应时间），且查询指标应该返回正确的统计数据。

**验证需求：7.2, 7.5**

### 属性 24：指标超过阈值触发告警

*对于任何*监控指标（失败率、响应时间），当指标值超过配置的阈值时，系统应该触发相应的告警通知。

**验证需求：7.3, 7.4**

### 属性 25：执行前请求治理验证

*对于任何*代理执行请求，系统应该在触发执行前向治理层请求权限验证，并传递完整的执行上下文（来源、用户、时间、代理 ID）。

**验证需求：8.1, 8.4**

### 属性 26：应用治理策略限制

*对于任何*治理层返回的策略限制（速率限制、配额控制），系统应该正确应用这些限制并在超出限制时拒绝请求。

**验证需求：8.2**

### 属性 27：幂等性键检查

*对于任何*包含幂等性键的请求，系统应该在处理前检查该键是否已被处理过。

**验证需求：9.1**

### 属性 28：幂等性保证

*对于任何*幂等性键，使用相同幂等性键发送多次请求应该返回相同的执行结果，且代理只被执行一次。

**验证需求：9.2**

### 属性 29：失败自动重试

*对于任何*配置了重试策略的端点，当代理执行失败时，系统应该根据策略（最大尝试次数、退避算法）自动重试。

**验证需求：9.3, 9.4**

### 属性 30：重试日志记录

*对于任何*触发重试的执行，系统应该记录所有重试尝试（尝试次数、时间、结果）和最终结果。

**验证需求：9.5**

### 属性 31：配置加载和应用

*对于任何*有效的配置文件，系统应该正确加载全局设置（超时、重试次数、日志级别）并应用到系统行为中。

**验证需求：10.1**

### 属性 32：端点独立配置

*对于任何*端点，其配置（认证方式、转换规则、执行模式）应该独立生效，不影响其他端点的行为。

**验证需求：10.2**

### 属性 33：配置版本回滚往返

*对于任何*配置更新，更新配置后执行回滚应该恢复到更新前的配置状态。

**验证需求：10.5**

## 错误处理

### 错误分类

系统定义以下错误类别：

1. **客户端错误 (4xx)**
   - 400 Bad Request：负载格式错误、解析失败
   - 401 Unauthorized：认证令牌无效或缺失
   - 403 Forbidden：签名验证失败、治理层拒绝
   - 404 Not Found：端点不存在
   - 429 Too Many Requests：速率限制超出

2. **服务器错误 (5xx)**
   - 500 Internal Server Error：系统内部错误
   - 503 Service Unavailable：Agent Runtime 不可用
   - 504 Gateway Timeout：执行超时

### 错误响应格式

所有错误响应遵循统一格式：

```typescript
interface ErrorResponse {
  error: {
    code: string          // 错误代码，如 "INVALID_TOKEN"
    message: string       // 人类可读的错误消息
    details?: any         // 可选的详细错误信息
    requestId: string     // 请求 ID，用于追踪
    timestamp: string     // ISO 8601 格式的时间戳
  }
}
```

### 错误处理策略

1. **验证错误**：立即返回，不记录到执行表
2. **转换错误**：记录到事件日志，返回详细错误信息
3. **执行错误**：根据重试策略决定是否重试
4. **系统错误**：记录完整堆栈跟踪，触发告警

### 超时处理

- **请求超时**：可配置的 HTTP 请求超时（默认 30 秒）
- **执行超时**：可配置的代理执行超时（默认 5 分钟）
- **同步模式超时**：如果执行超时，返回 504 错误，但执行继续在后台运行

### 重试策略

```typescript
interface RetryPolicy {
  maxAttempts: number        // 最大重试次数（默认 3）
  initialDelay: number       // 初始延迟（默认 1000ms）
  maxDelay: number          // 最大延迟（默认 30000ms）
  backoffMultiplier: number // 退避乘数（默认 2）
  retryableErrors: string[] // 可重试的错误代码
}

// 重试延迟计算：min(initialDelay * (backoffMultiplier ^ attempt), maxDelay)
```

可重试的错误：
- 503 Service Unavailable
- 504 Gateway Timeout
- 网络连接错误
- 临时性系统错误

不可重试的错误：
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found

## 测试策略

### 双重测试方法

系统测试采用单元测试和基于属性的测试相结合的方法：

- **单元测试**：验证特定示例、边缘情况和错误条件
- **属性测试**：验证跨所有输入的通用属性
- 两者互补，共同提供全面覆盖

### 单元测试重点

单元测试应该专注于：
- 特定的示例场景（如特定的 JSON 负载格式）
- 组件之间的集成点（如与 Agent Runtime 的交互）
- 边缘情况（如空负载、超大负载）
- 错误条件（如网络故障、超时）

避免编写过多的单元测试 - 属性测试已经处理了大量输入覆盖。

### 基于属性的测试

使用 **fast-check**（TypeScript）或等效的属性测试库。

**配置要求**：
- 每个属性测试最少运行 100 次迭代
- 每个测试必须引用设计文档中的属性
- 标签格式：**Feature: triggers-webhook, Property {number}: {property_text}**

**测试覆盖**：
- 端点管理操作（创建、查询、更新、删除）
- 认证和签名验证
- 负载解析和转换
- 执行触发和响应处理
- 幂等性保证
- 错误处理和重试逻辑
- 日志记录和监控

### 集成测试

集成测试验证系统与外部组件的交互：

1. **与 Agent Runtime 集成**
   - 模拟 Agent Runtime 的各种响应
   - 验证执行请求的正确性
   - 测试超时和错误处理

2. **与 Governance Layer 集成**
   - 模拟权限验证和策略限制
   - 验证上下文传递的完整性
   - 测试拒绝场景

3. **数据库集成**
   - 验证数据持久化
   - 测试并发访问
   - 验证事务完整性

### 性能测试

虽然不在单元测试范围内，但应该进行以下性能测试：

- **负载测试**：模拟高并发请求
- **压力测试**：测试系统极限
- **持久性测试**：长时间运行验证稳定性

### 安全测试

- **认证绕过测试**：尝试各种认证绕过方法
- **注入攻击测试**：测试 SQL 注入、XSS 等
- **DoS 防护测试**：验证速率限制和资源保护

### 测试数据生成

使用属性测试库的生成器创建测试数据：

```typescript
// 示例：生成随机端点配置
const endpointConfigArbitrary = fc.record({
  name: fc.string({ minLength: 1, maxLength: 255 }),
  targetAgentId: fc.uuid(),
  authMethod: fc.oneof(
    fc.record({ type: fc.constant('bearer'), token: fc.string() }),
    fc.record({ 
      type: fc.constant('hmac'), 
      secret: fc.string(),
      algorithm: fc.constantFrom('sha256', 'sha512')
    })
  ),
  executionMode: fc.constantFrom('sync', 'async'),
  enabled: fc.boolean()
})
```

### 测试环境

- **本地开发**：使用内存数据库和模拟的外部服务
- **CI/CD**：使用容器化的测试环境
- **集成环境**：使用真实的 Agent Runtime 和 Governance Layer 实例

### 测试覆盖率目标

- 代码覆盖率：>80%
- 分支覆盖率：>75%
- 属性测试覆盖：所有 33 个正确性属性
- 集成测试覆盖：所有外部接口
