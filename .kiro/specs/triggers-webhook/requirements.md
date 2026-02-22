# 需求文档：Webhook 触发器

> **目标**：通过统一的 Python Webhook 入口安全触发 Agent Run，并与治理层、运行时、审计链路集成  
> **优先级**：P1  
> **预估工作量**：7-10 天

## 简介

Webhook 触发器系统允许外部系统通过 HTTP Webhook 触发 OwlClaw Agent 的执行。该系统提供端点注册、请求验证、负载转换、代理执行触发、响应处理和事件监控等功能，并与 agent-runtime 和治理层集成。

## 技术栈约束（统一）

- Webhook 触发器核心实现统一使用 **Python**，并落在 OwlClaw 主仓（`owlclaw/`）内。
- HTTP 接入层采用 Python Web 框架（FastAPI/Starlette 兼容方案），测试采用 `pytest`。
- 数据访问层统一使用项目既有数据库基础设施（SQLAlchemy + Alembic），不引入独立 ORM 技术栈分叉。
- 如需多语言接入（Node/TS 等），通过**外部适配器**转发到 OwlClaw HTTP/API 入口，不在核心触发器模块内引入多语言运行时。

## 术语表

- **Webhook_System**: Webhook 触发器系统，负责接收和处理外部 HTTP 请求
- **Webhook_Endpoint**: Webhook 端点，用于接收外部系统的 HTTP 请求
- **Agent_Runtime**: 代理运行时，负责执行代理任务
- **Governance_Layer**: 治理层，负责权限控制和策略管理
- **Payload**: 负载，HTTP 请求中携带的数据
- **Authentication_Token**: 认证令牌，用于验证请求来源的凭证
- **Event_Log**: 事件日志，记录 Webhook 事件的详细信息
- **Transformation_Rule**: 转换规则，定义如何将 Webhook 负载转换为代理输入

## 需求

### 需求 1：Webhook 端点注册

**用户故事：** 作为系统管理员，我希望能够注册和管理 Webhook 端点，以便外部系统可以触发代理执行。

#### 验收标准

1. WHEN 管理员创建新的 Webhook 端点时，THE Webhook_System SHALL 生成唯一的端点 URL 和 Authentication_Token
2. WHEN 管理员配置 Webhook 端点时，THE Webhook_System SHALL 允许指定目标代理、转换规则和认证方式
3. WHEN 管理员查询 Webhook 端点列表时，THE Webhook_System SHALL 返回所有已注册端点的配置信息
4. WHEN 管理员更新 Webhook 端点配置时，THE Webhook_System SHALL 验证配置有效性并保存更改
5. WHEN 管理员删除 Webhook 端点时，THE Webhook_System SHALL 撤销该端点并拒绝后续请求

### 需求 2：HTTP 请求验证

**用户故事：** 作为系统管理员，我希望系统能够验证传入的 HTTP 请求，以确保只有授权的外部系统可以触发代理。

#### 验收标准

1. WHEN 接收到 HTTP 请求时，THE Webhook_System SHALL 验证请求的 Authentication_Token 是否有效
2. WHEN 请求包含签名时，THE Webhook_System SHALL 使用配置的密钥验证签名的正确性
3. IF Authentication_Token 无效或缺失，THEN THE Webhook_System SHALL 返回 401 未授权错误
4. IF 请求签名验证失败，THEN THE Webhook_System SHALL 返回 403 禁止访问错误
5. WHEN 请求来自未知端点时，THE Webhook_System SHALL 返回 404 未找到错误

### 需求 3：负载解析和转换

**用户故事：** 作为系统集成开发者，我希望系统能够解析和转换 Webhook 负载，以便将外部数据格式转换为代理可以理解的输入格式。

#### 验收标准

1. WHEN 接收到 JSON 格式的 Payload 时，THE Webhook_System SHALL 解析 JSON 数据为结构化对象
2. WHEN 接收到 XML 格式的 Payload 时，THE Webhook_System SHALL 解析 XML 数据为结构化对象
3. WHEN 接收到 form-urlencoded 格式的 Payload 时，THE Webhook_System SHALL 解析表单数据为键值对
4. WHEN 应用 Transformation_Rule 时，THE Webhook_System SHALL 将解析后的数据转换为代理输入格式
5. IF Payload 解析失败，THEN THE Webhook_System SHALL 返回 400 错误请求错误并包含详细错误信息

### 需求 4：代理执行触发

**用户故事：** 作为系统集成开发者，我希望 Webhook 能够触发代理执行，以便外部事件可以自动启动代理任务。

#### 验收标准

1. WHEN Webhook 请求验证通过且负载转换完成时，THE Webhook_System SHALL 调用 Agent_Runtime 执行指定代理
2. WHEN 触发代理执行时，THE Webhook_System SHALL 传递转换后的输入数据和执行上下文
3. WHEN 代理执行启动时，THE Webhook_System SHALL 返回执行 ID 和初始状态
4. WHEN Governance_Layer 拒绝执行时，THE Webhook_System SHALL 返回 403 禁止访问错误
5. IF Agent_Runtime 不可用，THEN THE Webhook_System SHALL 返回 503 服务不可用错误

### 需求 5：响应处理

**用户故事：** 作为外部系统开发者，我希望能够接收到 Webhook 请求的响应，以便了解代理执行的状态和结果。

#### 验收标准

1. WHEN 代理执行成功启动时，THE Webhook_System SHALL 返回 202 已接受状态码和执行详情
2. WHEN 请求处理失败时，THE Webhook_System SHALL 返回适当的 HTTP 错误状态码和错误详情
3. WHEN 返回响应时，THE Webhook_System SHALL 包含执行 ID、状态和时间戳信息
4. WHERE 配置了同步执行模式，THE Webhook_System SHALL 等待代理执行完成并返回最终结果
5. WHERE 配置了异步执行模式，THE Webhook_System SHALL 立即返回执行 ID 而不等待完成

### 需求 6：事件日志记录

**用户故事：** 作为系统管理员，我希望系统能够记录所有 Webhook 事件，以便进行审计、调试和监控。

#### 验收标准

1. WHEN 接收到 Webhook 请求时，THE Webhook_System SHALL 记录请求的时间戳、来源 IP、端点 ID 和请求头
2. WHEN 处理 Webhook 请求时，THE Webhook_System SHALL 记录验证结果、转换过程和执行状态
3. WHEN 代理执行完成时，THE Webhook_System SHALL 记录执行结果、耗时和资源使用情况
4. WHEN 发生错误时，THE Webhook_System SHALL 记录错误类型、错误消息和堆栈跟踪
5. THE Webhook_System SHALL 将所有 Event_Log 持久化存储以供后续查询和分析

### 需求 7：监控和告警

**用户故事：** 作为系统运维人员，我希望能够监控 Webhook 系统的运行状态，以便及时发现和处理异常情况。

#### 验收标准

1. THE Webhook_System SHALL 暴露健康检查端点以供监控系统查询
2. THE Webhook_System SHALL 记录请求成功率、失败率和平均响应时间等指标
3. WHEN 请求失败率超过阈值时，THE Webhook_System SHALL 触发告警通知
4. WHEN 响应时间超过阈值时，THE Webhook_System SHALL 触发性能告警
5. THE Webhook_System SHALL 提供查询接口以获取实时和历史监控数据

### 需求 8：与治理层集成

**用户故事：** 作为安全管理员，我希望 Webhook 系统能够与治理层集成，以确保所有触发的代理执行都符合安全策略和权限控制。

#### 验收标准

1. WHEN 触发代理执行前，THE Webhook_System SHALL 向 Governance_Layer 请求执行权限验证
2. WHEN Governance_Layer 返回策略限制时，THE Webhook_System SHALL 应用速率限制和配额控制
3. WHEN 执行被拒绝时，THE Webhook_System SHALL 记录拒绝原因并返回适当的错误响应
4. THE Webhook_System SHALL 将执行上下文（包括来源、用户、时间）传递给 Governance_Layer
5. THE Webhook_System SHALL 遵守 Governance_Layer 定义的数据访问和隐私策略

### 需求 9：重试和幂等性

**用户故事：** 作为外部系统开发者，我希望系统能够处理重复请求和支持重试机制，以确保在网络不稳定情况下的可靠性。

#### 验收标准

1. WHEN 接收到包含幂等性键的请求时，THE Webhook_System SHALL 检查该键是否已被处理
2. IF 幂等性键已存在，THEN THE Webhook_System SHALL 返回原始执行结果而不重复执行
3. WHEN 代理执行失败且配置了重试策略时，THE Webhook_System SHALL 根据策略自动重试
4. THE Webhook_System SHALL 在重试时应用指数退避算法以避免系统过载
5. THE Webhook_System SHALL 记录所有重试尝试和最终结果

### 需求 10：配置管理

**用户故事：** 作为系统管理员，我希望能够灵活配置 Webhook 系统的行为，以适应不同的使用场景和安全要求。

#### 验收标准

1. THE Webhook_System SHALL 支持通过配置文件定义全局设置（如超时、重试次数、日志级别）
2. THE Webhook_System SHALL 支持为每个端点单独配置认证方式、转换规则和执行模式
3. WHEN 配置更新时，THE Webhook_System SHALL 验证配置的有效性和完整性
4. WHEN 配置更新时，THE Webhook_System SHALL 在不中断服务的情况下应用新配置
5. THE Webhook_System SHALL 提供配置版本管理和回滚功能

## 功能需求（FR）

- **FR-1：Webhook 端点注册与管理**（对应需求 1）
- **FR-2：请求认证与签名验证**（对应需求 2）
- **FR-3：负载解析与转换**（对应需求 3）
- **FR-4：Agent 执行触发与上下文传递**（对应需求 4）
- **FR-5：同步/异步响应处理**（对应需求 5）
- **FR-6：事件日志持久化与查询**（对应需求 6）
- **FR-7：监控指标与告警**（对应需求 7）
- **FR-8：治理层集成与策略执行**（对应需求 8）
- **FR-9：幂等与重试机制**（对应需求 9）
- **FR-10：配置加载、校验与版本管理**（对应需求 10）

## 非功能需求（NFR）

- **NFR-1：技术栈一致性**  
  核心实现必须保持 Python 单栈；Node/TypeScript 仅可作为外部适配层。
- **NFR-2：可靠性**  
  在网络波动、运行时短暂不可用场景下，系统应具备可恢复性并保留可追踪执行记录。
- **NFR-3：可观测性**  
  所有关键路径应可被日志、指标与审计事件追踪，便于问题定位。
- **NFR-4：安全性**  
  默认启用认证校验、签名校验和治理验证，不允许未授权执行。

## 验收标准总览

### 功能验收
- [ ] **FR-1**：端点 CRUD 完整可用，唯一 URL/Token 正确生成
- [ ] **FR-2**：认证失败返回 401，签名失败返回 403，未知端点返回 404
- [ ] **FR-3**：JSON/XML/Form 解析与转换规则执行正确，错误返回 400
- [ ] **FR-4**：验证通过后可触发 Agent Runtime 并传递完整执行上下文
- [ ] **FR-5**：同步/异步模式行为正确，响应结构一致
- [ ] **FR-6**：请求、转换、执行、错误日志完整持久化
- [ ] **FR-7**：健康检查、指标统计、阈值告警可用
- [ ] **FR-8**：治理拒绝可拦截执行并返回合规错误
- [ ] **FR-9**：幂等键生效，重试具备指数退避与记录
- [ ] **FR-10**：配置校验、热更新与回滚流程可执行

### 非功能验收
- [ ] **NFR-1**：核心模块不引入 Node/TypeScript 运行时依赖
- [ ] **NFR-2**：故障场景下系统可降级且不丢审计数据
- [ ] **NFR-3**：可观测链路覆盖请求到执行全流程
- [ ] **NFR-4**：未授权请求无法触发 Agent 执行
