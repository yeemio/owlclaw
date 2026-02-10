# 需求文档

## 简介

本文档定义 OwlClaw Agent 内建工具的需求。内建工具是 Agent 的核心能力，使 Agent 能够自我调度、管理记忆、查询状态和记录决策。这些工具通过 LLM function calling 暴露给 Agent，让 Agent 自主决定何时使用。

内建工具包括：
- **schedule_once** / **schedule_cron** / **cancel_schedule** — 自我调度工具
- **remember** / **recall** — 记忆管理工具
- **query_state** — 状态查询工具
- **log_decision** — 决策记录工具

## 术语表

- **Built-in_Tool**: Agent 内建工具，区别于业务 capabilities
- **Self_Scheduling**: Agent 自我调度能力，通过 schedule_once/schedule_cron 实现
- **Memory_System**: Agent 的记忆系统，包括短期记忆（当前 run）和长期记忆（跨 run）
- **MEMORY.md**: 长期记忆的持久化文件
- **Vector_Search**: 向量搜索，用于检索相关记忆
- **State_Provider**: 业务应用注册的状态提供者（@state 装饰器）
- **Decision_Log**: Agent 决策理由的记录
- **Hatchet_Integration**: 与 Hatchet 的集成，用于持久化调度
- **Agent_Run**: Agent 的一次执行周期

## 需求

### 需求 1：schedule_once 工具 — 一次性延迟调度

**用户故事：** 作为 Agent，我希望能够调度一次性的延迟任务，以便在未来某个时间点继续执行。

#### 验收标准

1. THE schedule_once tool SHALL 接受 delay_seconds 和 focus 参数
2. WHEN Agent 调用 schedule_once 时，THE System SHALL 通过 Hatchet 创建延迟任务
3. WHEN delay_seconds 到期时，THE System SHALL 触发新的 Agent Run
4. WHEN 新的 Agent Run 启动时，THE System SHALL 在 context 中包含 focus 信息
5. THE schedule_once tool SHALL 返回调度任务的唯一 ID
6. WHEN delay_seconds 为负数或零时，THE System SHALL 返回验证错误
7. THE schedule_once tool SHALL 支持最小延迟 1 秒，最大延迟 30 天
8. WHEN 调度成功时，THE System SHALL 记录到 Ledger

#### Function Calling Schema

```json
{
  "name": "schedule_once",
  "description": "Schedule a one-time delayed Agent run. Use this when you need to check something later or wait for an event.",
  "parameters": {
    "type": "object",
    "properties": {
      "delay_seconds": {
        "type": "integer",
        "description": "Delay in seconds before the next Agent run (minimum: 1, maximum: 2592000)",
        "minimum": 1,
        "maximum": 2592000
      },
      "focus": {
        "type": "string",
        "description": "What to focus on in the next run (e.g., 'check entry opportunities', 'review market state')"
      }
    },
    "required": ["delay_seconds", "focus"]
  }
}
```

### 需求 2：schedule_cron 工具 — 周期性调度

**用户故事：** 作为 Agent，我希望能够设置周期性任务，以便定期执行某些检查。

#### 验收标准

1. THE schedule_cron tool SHALL 接受 cron_expression 和 focus 参数
2. WHEN Agent 调用 schedule_cron 时，THE System SHALL 通过 Hatchet 创建 cron 任务
3. WHEN cron 表达式触发时，THE System SHALL 启动新的 Agent Run
4. THE schedule_cron tool SHALL 验证 cron 表达式格式
5. THE schedule_cron tool SHALL 返回调度任务的唯一 ID
6. WHEN cron 表达式无效时，THE System SHALL 返回验证错误
7. THE schedule_cron tool SHALL 支持标准 cron 格式（分 时 日 月 周）
8. WHEN 调度成功时，THE System SHALL 记录到 Ledger

#### Function Calling Schema

```json
{
  "name": "schedule_cron",
  "description": "Schedule a recurring Agent run using cron expression. Use this for periodic checks (e.g., every hour during trading hours).",
  "parameters": {
    "type": "object",
    "properties": {
      "cron_expression": {
        "type": "string",
        "description": "Cron expression (format: 'minute hour day month weekday', e.g., '0 9 * * 1-5' for 9am on weekdays)"
      },
      "focus": {
        "type": "string",
        "description": "What to focus on in each run (e.g., 'morning market analysis', 'hourly position check')"
      }
    },
    "required": ["cron_expression", "focus"]
  }
}
```

### 需求 3：cancel_schedule 工具 — 取消已调度任务

**用户故事：** 作为 Agent，我希望能够取消之前调度的任务，以便在情况变化时停止不必要的执行。

#### 验收标准

1. THE cancel_schedule tool SHALL 接受 schedule_id 参数
2. WHEN Agent 调用 cancel_schedule 时，THE System SHALL 通过 Hatchet 取消对应任务
3. WHEN 任务尚未执行时，THE System SHALL 成功取消并从队列移除
4. WHEN 任务正在执行时，THE System SHALL 发送取消信号
5. WHEN 任务已完成或不存在时，THE System SHALL 返回错误信息
6. THE cancel_schedule tool SHALL 返回取消是否成功
7. WHEN 取消成功时，THE System SHALL 记录到 Ledger

#### Function Calling Schema

```json
{
  "name": "cancel_schedule",
  "description": "Cancel a previously scheduled Agent run. Use this when the scheduled task is no longer needed.",
  "parameters": {
    "type": "object",
    "properties": {
      "schedule_id": {
        "type": "string",
        "description": "The ID returned by schedule_once or schedule_cron"
      }
    },
    "required": ["schedule_id"]
  }
}
```


### 需求 4：remember 工具 — 写入长期记忆

**用户故事：** 作为 Agent，我希望能够主动记住重要的经验和教训，以便在未来的决策中参考。

#### 验收标准

1. THE remember tool SHALL 接受 content 和可选的 tags 参数
2. WHEN Agent 调用 remember 时，THE System SHALL 将内容写入 MEMORY.md
3. THE System SHALL 自动为记忆条目添加时间戳
4. THE System SHALL 将记忆内容索引到向量数据库
5. THE remember tool SHALL 支持多标签分类（如 ["trading", "lesson", "market_crash"]）
6. WHEN content 为空时，THE System SHALL 返回验证错误
7. THE remember tool SHALL 限制单条记忆最大长度为 2000 字符
8. WHEN 写入成功时，THE System SHALL 返回记忆条目的唯一 ID
9. THE System SHALL 记录到 Ledger

#### Function Calling Schema

```json
{
  "name": "remember",
  "description": "Store important information in long-term memory. Use this to remember lessons, patterns, or decisions for future reference.",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "What to remember (e.g., 'After sharp market drop, rebound signals are usually accurate within 2 hours')",
        "maxLength": 2000
      },
      "tags": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Optional tags for categorization (e.g., ['trading', 'lesson', 'volatility'])"
      }
    },
    "required": ["content"]
  }
}
```

### 需求 5：recall 工具 — 搜索长期记忆

**用户故事：** 作为 Agent，我希望能够搜索历史记忆，以便在当前决策中参考过去的经验。

#### 验收标准

1. THE recall tool SHALL 接受 query 和可选的 limit 参数
2. WHEN Agent 调用 recall 时，THE System SHALL 使用向量搜索查找相关记忆
3. THE System SHALL 按相关性排序返回结果
4. THE System SHALL 支持时间衰减（最近的记忆权重更高）
5. THE recall tool SHALL 默认返回最多 5 条记忆
6. THE recall tool SHALL 支持最多返回 20 条记忆
7. WHEN 没有相关记忆时，THE System SHALL 返回空列表
8. THE System SHALL 在返回结果中包含记忆内容、时间戳、标签和相关性分数
9. THE System SHALL 记录到 Ledger

#### Function Calling Schema

```json
{
  "name": "recall",
  "description": "Search long-term memory for relevant past experiences. Use this when you need to remember similar situations or lessons.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "What to search for (e.g., 'market crash recovery patterns', 'entry timing lessons')"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of memories to return (default: 5, max: 20)",
        "minimum": 1,
        "maximum": 20,
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

### 需求 6：query_state 工具 — 查询业务状态

**用户故事：** 作为 Agent，我希望能够查询业务应用的当前状态，以便基于最新信息做决策。

#### 验收标准

1. THE query_state tool SHALL 接受 state_name 参数
2. WHEN Agent 调用 query_state 时，THE System SHALL 调用对应的 @state 装饰器注册的状态提供者
3. THE System SHALL 返回状态提供者的执行结果
4. WHEN state_name 不存在时，THE System SHALL 返回错误信息
5. THE System SHALL 支持状态提供者的异步执行
6. THE System SHALL 设置状态查询超时（默认 30 秒）
7. WHEN 状态查询超时时，THE System SHALL 返回超时错误
8. THE System SHALL 记录到 Ledger（包括查询耗时）
9. THE System SHALL 支持状态结果缓存（可选，由状态提供者配置）

#### Function Calling Schema

```json
{
  "name": "query_state",
  "description": "Query current business state. Use this to get up-to-date information before making decisions.",
  "parameters": {
    "type": "object",
    "properties": {
      "state_name": {
        "type": "string",
        "description": "Name of the state to query (e.g., 'market_state', 'position_summary', 'account_balance')"
      }
    },
    "required": ["state_name"]
  }
}
```

### 需求 7：log_decision 工具 — 记录决策理由

**用户故事：** 作为 Agent，我希望能够记录我的决策理由，以便后续审计和分析。

#### 验收标准

1. THE log_decision tool SHALL 接受 reasoning 和可选的 decision_type 参数
2. WHEN Agent 调用 log_decision 时，THE System SHALL 将决策理由写入 Ledger
3. THE System SHALL 自动关联当前 Agent Run 的上下文
4. THE System SHALL 支持决策类型分类（如 "capability_selection", "schedule_decision", "no_action"）
5. THE log_decision tool SHALL 限制 reasoning 最大长度为 1000 字符
6. WHEN reasoning 为空时，THE System SHALL 返回验证错误
7. THE System SHALL 在 Ledger 中标记该条记录为 "decision_log" 类型
8. THE System SHALL 返回决策日志的唯一 ID

#### Function Calling Schema

```json
{
  "name": "log_decision",
  "description": "Log your decision reasoning for audit and analysis. Use this to explain why you chose a particular action or decided not to act.",
  "parameters": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "Explanation of your decision (e.g., 'Market volatility is too high, waiting for stabilization before entry')",
        "maxLength": 1000
      },
      "decision_type": {
        "type": "string",
        "enum": ["capability_selection", "schedule_decision", "no_action", "other"],
        "description": "Type of decision being logged",
        "default": "other"
      }
    },
    "required": ["reasoning"]
  }
}
```

### 需求 8：错误处理和边界条件

**用户故事：** 作为系统管理员，我希望内建工具能够优雅地处理错误和边界条件，以便 Agent 能够可靠运行。

#### 验收标准

1. WHEN 任何内建工具执行失败时，THE System SHALL 返回结构化错误信息
2. THE System SHALL 区分用户错误（如参数验证失败）和系统错误（如数据库连接失败）
3. WHEN 系统错误发生时，THE System SHALL 记录详细错误日志
4. THE System SHALL 为每个工具设置执行超时
5. WHEN 工具执行超时时，THE System SHALL 返回超时错误并清理资源
6. THE System SHALL 支持工具执行的重试机制（仅针对幂等操作）
7. WHEN 并发调用同一工具时，THE System SHALL 保证数据一致性
8. THE System SHALL 限制单次 Agent Run 中工具调用的总次数（防止死循环）

### 需求 9：与其他组件的集成

**用户故事：** 作为开发者，我希望内建工具能够与 OwlClaw 的其他组件无缝集成。

#### 验收标准

1. THE schedule_once/schedule_cron tools SHALL 通过 Hatchet 集成实现持久化调度
2. THE remember/recall tools SHALL 使用业务应用配置的向量数据库
3. THE query_state tool SHALL 调用 capabilities.registry 中注册的状态提供者
4. THE log_decision tool SHALL 写入 governance.ledger
5. ALL tools SHALL 通过 governance.visibility 过滤（虽然内建工具通常总是可见）
6. ALL tools SHALL 支持 Langfuse tracing
7. THE System SHALL 在 Agent Run 的 system prompt 中包含所有可用内建工具的 schema
8. THE System SHALL 支持内建工具的动态启用/禁用（通过配置）

### 需求 10：性能和可扩展性

**用户故事：** 作为系统管理员，我希望内建工具能够高效运行，支持大规模部署。

#### 验收标准

1. THE recall tool SHALL 支持向量搜索的批量查询优化
2. THE query_state tool SHALL 支持状态结果缓存（TTL 可配置）
3. THE remember tool SHALL 支持异步写入（不阻塞 Agent Run）
4. THE System SHALL 限制 MEMORY.md 文件大小（超过阈值时自动归档）
5. THE System SHALL 支持记忆的自动清理策略（如删除 1 年前的记忆）
6. THE schedule_once/schedule_cron tools SHALL 支持高并发调度（依赖 Hatchet）
7. THE System SHALL 监控工具执行的性能指标（延迟、成功率、错误率）
8. THE System SHALL 支持工具执行的限流（防止滥用）

### 需求 11：测试和验证

**用户故事：** 作为开发者，我希望内建工具有完善的测试覆盖，以便保证质量。

#### 验收标准

1. THE System SHALL 提供单元测试覆盖所有内建工具的核心逻辑
2. THE System SHALL 提供集成测试验证工具与 Hatchet/Ledger/Memory 的集成
3. THE System SHALL 提供端到端测试模拟 Agent 调用工具的完整流程
4. THE System SHALL 提供性能测试验证工具在高负载下的表现
5. THE System SHALL 提供错误注入测试验证错误处理的健壮性
6. THE System SHALL 提供文档示例代码的可执行测试

### 需求 12：安全考虑

**用户故事：** 作为安全工程师，我希望内建工具不会成为安全漏洞的入口。

#### 验收标准

1. THE remember tool SHALL 对 content 进行 sanitization（防止注入攻击）
2. THE query_state tool SHALL 限制可查询的状态范围（不暴露敏感内部状态）
3. THE schedule_once/schedule_cron tools SHALL 限制调度频率（防止资源耗尽）
4. THE System SHALL 记录所有工具调用到审计日志
5. THE System SHALL 支持工具调用的权限控制（企业版）
6. THE cancel_schedule tool SHALL 验证 Agent 只能取消自己创建的调度
7. THE System SHALL 对工具参数进行严格的类型和范围验证
8. THE System SHALL 防止通过工具参数进行 Prompt Injection

## 非功能性需求

### 性能

- 工具调用延迟 P95 < 500ms（不包括状态查询的业务逻辑耗时）
- 向量搜索（recall）延迟 P95 < 200ms
- 支持单个 Agent 实例每秒 10+ 次工具调用
- 记忆写入（remember）支持异步，不阻塞 Agent Run

### 可靠性

- 工具执行成功率 > 99.9%
- 调度任务不丢失（依赖 Hatchet 的持久化保证）
- 记忆数据不丢失（依赖数据库的持久化保证）
- 支持工具执行的自动重试（幂等操作）

### 可维护性

- 每个工具的实现独立，易于测试和修改
- 工具的 function calling schema 与实现代码自动同步
- 提供清晰的错误信息和日志
- 支持工具的版本演进（向后兼容）

### 可扩展性

- 支持添加新的内建工具（通过插件机制）
- 支持工具的自定义配置（如超时、重试策略）
- 支持工具的 A/B 测试（不同 Agent 实例使用不同工具版本）

## 依赖

- **owlclaw.integrations.hatchet** — 调度工具依赖 Hatchet 集成
- **owlclaw.governance.ledger** — 所有工具依赖 Ledger 记录
- **owlclaw.capabilities.registry** — query_state 依赖状态提供者注册
- **向量数据库** — recall 依赖向量搜索（业务应用配置）
- **PostgreSQL** — 记忆和 Ledger 的持久化存储

## 约束

- 内建工具的 function calling schema 必须遵循 OpenAI function calling 规范
- 工具名称必须是有效的 Python 标识符（snake_case）
- 工具描述必须清晰，帮助 LLM 理解何时使用
- 工具参数必须有详细的 description（LLM 依赖这些信息做决策）
- 工具执行必须是幂等的（除了 remember 和 log_decision）

## 验收测试场景

### 场景 1：Agent 自我调度检查入场机会

```
GIVEN Agent 在盘中检查入场机会
WHEN Agent 发现当前无机会，但市场波动较大
THEN Agent 调用 schedule_once(300, "check entry opportunities")
AND 5 分钟后 Agent Run 被触发
AND 新的 Agent Run 的 context 包含 "check entry opportunities"
```

### 场景 2：Agent 记住并回忆经验

```
GIVEN Agent 在市场急跌后发现反弹信号准确
WHEN Agent 调用 remember("After sharp drop, rebound signals accurate within 2h", tags=["trading", "lesson"])
THEN 记忆被写入 MEMORY.md 和向量数据库
AND 下次市场急跌时，Agent 调用 recall("market crash recovery")
AND recall 返回之前的经验
```

### 场景 3：Agent 查询状态后决策

```
GIVEN Agent 收到周期性检查事件
WHEN Agent 调用 query_state("market_state")
AND 返回 {"is_trading_time": false}
THEN Agent 调用 log_decision("Non-trading hours, skipping check", decision_type="no_action")
AND 不调用任何业务 capability
```

### 场景 4：Agent 取消不必要的调度

```
GIVEN Agent 之前调度了 schedule_id="abc123" 的任务
WHEN 市场情况发生变化，该任务不再需要
THEN Agent 调用 cancel_schedule("abc123")
AND Hatchet 任务被取消
AND 该任务不会再执行
```

## 参考

- OpenClaw 的 memory-tool.ts 和 schedule-tool.ts
- Agent Skills 规范（agentskills.io）
- OpenAI Function Calling 文档
- Hatchet Python SDK 文档
- OwlClaw 架构文档 `docs/ARCHITECTURE_ANALYSIS.md` §5.2.1（Agent 内建工具）
