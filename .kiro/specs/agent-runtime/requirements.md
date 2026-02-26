# 需求文档

## 文档联动

- requirements: `.kiro/specs/agent-runtime/requirements.md`
- design: `.kiro/specs/agent-runtime/design.md`
- tasks: `.kiro/specs/agent-runtime/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 简介

本文档定义 OwlClaw Agent 运行时核心模块的需求。Agent 运行时是 OwlClaw 的核心，负责 Agent 的身份加载、记忆系统、知识注入、function calling 决策循环和 Heartbeat 机制。

Agent 运行时使 Agent 成为一个**有身份、有记忆、有知识的持续实体**，而不是无状态的函数。Agent 通过 LLM function calling 自主决定何时使用哪些能力，而不是由外部循环控制。

核心能力：
- **身份加载** — 从 SOUL.md 和 IDENTITY.md 加载 Agent 的角色定位和能力范围
- **记忆系统** — 短期记忆（当前 run 上下文）和长期记忆（MEMORY.md + 向量搜索）
- **知识注入** — 将 Skills 的 SKILL.md 注入到 Agent 上下文，引导 Agent 理解业务语义
- **Function Calling 决策循环** — 基于 litellm 的 function calling 实现 Agent 自主决策
- **Heartbeat 机制** — 无事不调 LLM，只在有事件时触发决策

## 术语表

- **Agent_Runtime**: Agent 运行时，负责 Agent 的完整生命周期管理
- **Agent_Run**: Agent 的一次执行周期，从触发到完成
- **SOUL.md**: Agent 的角色定位和行为准则文档
- **IDENTITY.md**: Agent 管理的应用、能力范围、约束文档
- **MEMORY.md**: Agent 的长期记忆持久化文件
- **SKILL.md**: 遵循 Agent Skills 规范的业务知识文档
- **Short_Term_Memory**: 当前 run 的上下文（事件 + 状态 + 最近动作）
- **Long_Term_Memory**: 跨 run 的经验和教训（MEMORY.md + 向量搜索）
- **Knowledge_Injection**: 将 Skills 知识文档注入到 system prompt
- **Function_Calling**: LLM 从可见工具列表中选择动作的机制
- **Heartbeat**: 周期性检查是否有待处理事件，无事不调 LLM
- **Visible_Tools**: 经过治理过滤后 Agent 实际可见的工具列表
- **Built_In_Tools**: Agent 内建工具（schedule、memory、query_state 等）
- **Business_Capabilities**: 业务应用注册的能力（@handler 装饰器）
- **Agent_Skills_Spec**: Anthropic 发起的 Skills 知识文档开放规范
- **Progressive_Loading**: 渐进式加载 Skills（启动时加载 metadata，激活时加载完整指令）
- **Governance_Filtering**: 治理层对工具可见性的多层过滤
- **Trigger**: 唤醒 Agent 的事件（cron、webhook、schedule、heartbeat 等）


## 需求

### 需求 1：身份加载 — SOUL.md 和 IDENTITY.md

**用户故事：** 作为 Agent，我希望在启动时加载我的身份定义，以便知道我的角色定位、行为准则和能力范围。

#### 验收标准

1. WHEN Agent Runtime 初始化时，THE System SHALL 从应用目录加载 SOUL.md
2. WHEN Agent Runtime 初始化时，THE System SHALL 从应用目录加载 IDENTITY.md
3. THE System SHALL 验证 SOUL.md 和 IDENTITY.md 文件存在
4. WHEN SOUL.md 或 IDENTITY.md 不存在时，THE System SHALL 返回初始化错误
5. THE System SHALL 解析 SOUL.md 的内容为 Agent 的角色定位和行为准则
6. THE System SHALL 解析 IDENTITY.md 的内容为 Agent 的能力列表和约束
7. THE System SHALL 在每次 Agent Run 的 system prompt 中包含 SOUL.md 内容
8. THE System SHALL 在每次 Agent Run 的 system prompt 中包含 IDENTITY.md 的能力摘要
9. THE System SHALL 支持 SOUL.md 和 IDENTITY.md 的热重载（配置变更时无需重启）

### 需求 2：短期记忆 — 当前 Run 上下文

**用户故事：** 作为 Agent，我希望在当前 run 中能够访问本次执行的上下文信息，以便做出连贯的决策。

#### 验收标准

1. WHEN Agent Run 启动时，THE System SHALL 创建短期记忆上下文
2. THE System SHALL 在短期记忆中包含触发事件信息（trigger type、payload）
3. THE System SHALL 在短期记忆中包含 focus 信息（如果是调度触发）
4. THE System SHALL 在短期记忆中包含最近的工具调用历史（本次 run）
5. THE System SHALL 在短期记忆中包含最近的 LLM 响应（本次 run）
6. THE System SHALL 限制短期记忆的 token 数量（默认 2000 tokens）
7. WHEN 短期记忆超过 token 限制时，THE System SHALL 自动压缩（保留最重要的信息）
8. THE System SHALL 在 system prompt 中包含短期记忆内容
9. WHEN Agent Run 完成时，THE System SHALL 清理短期记忆

### 需求 3：长期记忆 — MEMORY.md 和向量搜索

**用户故事：** 作为 Agent，我希望能够持久化重要的经验和教训，并在未来的 run 中搜索相关记忆。

#### 验收标准

1. THE System SHALL 支持 MEMORY.md 文件的读写
2. WHEN Agent 调用 remember 工具时，THE System SHALL 将内容追加到 MEMORY.md
3. THE System SHALL 为每条记忆生成向量表示（embedding）
4. THE System SHALL 将向量表示索引到向量数据库
5. WHEN Agent 调用 recall 工具时，THE System SHALL 使用向量搜索查找相关记忆
6. THE System SHALL 按相关性和时间衰减排序返回记忆
7. THE System SHALL 支持记忆的标签分类（tags）
8. THE System SHALL 限制 MEMORY.md 文件大小（默认 10MB）
9. WHEN MEMORY.md 超过大小限制时，THE System SHALL 自动归档旧记忆
10. THE System SHALL 支持向量数据库的可配置（pgvector、Qdrant 等）
11. THE System SHALL 在 Agent Run 启动时预加载最相关的长期记忆（可选）

### 需求 4：知识注入 — Skills 的 SKILL.md

**用户故事：** 作为 Agent，我希望能够理解业务能力的语义和使用场景，而不仅仅是函数签名。

#### 验收标准

1. THE System SHALL 遵循 Agent Skills 规范（agentskills.io）加载 SKILL.md
2. WHEN Agent Runtime 初始化时，THE System SHALL 扫描所有注册的 capabilities
3. THE System SHALL 为每个 capability 加载对应的 SKILL.md frontmatter（metadata）
4. THE System SHALL 支持渐进式加载（启动时只加载 metadata，激活时加载完整指令）
5. WHEN Agent Run 启动时，THE System SHALL 根据上下文选择相关的 Skills
6. THE System SHALL 将选中的 Skills 的完整指令注入到 system prompt
7. THE System SHALL 支持 Skills 的 references/ 目录按需加载
8. THE System SHALL 限制单次注入的 Skills 总 token 数（默认 4000 tokens）
9. WHEN Skills 总 token 超过限制时，THE System SHALL 优先注入最相关的 Skills
10. THE System SHALL 支持 Skills 的热重载（SKILL.md 变更时无需重启）
11. THE System SHALL 验证 SKILL.md 的 frontmatter 格式（YAML + owlclaw 扩展字段）


### 需求 5：Function Calling 决策循环

**用户故事：** 作为 Agent，我希望能够通过 LLM function calling 自主选择动作，而不是由外部循环控制我的决策。

#### 验收标准

1. THE System SHALL 使用 litellm 统一调用 LLM 模型
2. WHEN Agent Run 启动时，THE System SHALL 构建包含所有可见工具的 system prompt
3. THE System SHALL 将可见工具的 function calling schema 传递给 LLM
4. THE System SHALL 支持 LLM 返回的 function call 请求
5. WHEN LLM 返回 function call 时，THE System SHALL 执行对应的工具
6. THE System SHALL 将工具执行结果返回给 LLM
7. THE System SHALL 支持 LLM 的多轮 function calling（直到 LLM 认为完成）
8. THE System SHALL 限制单次 Agent Run 的最大 function call 次数（默认 50 次）
9. WHEN function call 次数超过限制时，THE System SHALL 终止 run 并记录警告
10. THE System SHALL 支持 LLM 的流式响应（streaming）
11. THE System SHALL 记录每次 LLM 调用到 Langfuse（tracing）
12. THE System SHALL 支持 LLM 的超时控制（默认 60 秒）
13. WHEN LLM 调用超时时，THE System SHALL 终止 run 并记录错误

### 需求 6：可见工具列表构建

**用户故事：** 作为 Agent，我希望看到的工具列表是经过治理过滤的，符合我的权限和当前约束。

#### 验收标准

1. THE System SHALL 从 Capability Registry 获取所有注册的 business capabilities
2. THE System SHALL 从 Built-in Tools 获取所有内建工具
3. THE System SHALL 通过 Governance Layer 过滤工具列表
4. THE System SHALL 应用约束过滤（如 trading_hours_only）
5. THE System SHALL 应用预算过滤（月预算用完时隐藏高成本能力）
6. THE System SHALL 应用熔断过滤（连续失败时暂时隐藏）
7. THE System SHALL 应用限流过滤（频率超限时暂时隐藏）
8. THE System SHALL 应用角色过滤（Agent 角色权限范围内的能力）
9. THE System SHALL 将过滤后的工具列表转换为 function calling schema
10. THE System SHALL 在 system prompt 中包含可见工具的描述
11. THE System SHALL 记录工具可见性过滤的决策到 Ledger

### 需求 7：Heartbeat 机制

**用户故事：** 作为系统管理员，我希望 Agent 在无事时不调用 LLM，以节省成本和资源。

#### 验收标准

1. THE System SHALL 支持 Heartbeat 触发器（周期性检查）
2. WHEN Heartbeat 触发时，THE System SHALL 检查是否有待处理的事件
3. THE System SHALL 定义待处理事件的检查逻辑（可配置）
4. WHEN 没有待处理事件时，THE System SHALL 跳过 LLM 调用，直接结束 run
5. WHEN 有待处理事件时，THE System SHALL 启动完整的 Agent Run（包括 LLM 调用）
6. THE System SHALL 在 Heartbeat 检查中包含以下事件源：
   - 新的 webhook 事件
   - 新的 queue 消息
   - 数据库变更事件
   - 调度任务到期
   - 外部 API 通知
7. THE System SHALL 支持 Heartbeat 的频率配置（默认 5 分钟）
8. THE System SHALL 记录 Heartbeat 检查结果到 Ledger（是否有事件）
9. THE System SHALL 支持 Heartbeat 的动态启用/禁用

### 需求 8：Agent Run 生命周期管理

**用户故事：** 作为开发者，我希望 Agent Run 有清晰的生命周期阶段，便于监控和调试。

#### 验收标准

1. THE System SHALL 定义 Agent Run 的生命周期阶段：
   - INITIALIZING: 加载身份、记忆、知识
   - FILTERING: 构建可见工具列表
   - DECIDING: LLM function calling 决策
   - EXECUTING: 执行工具调用
   - REFLECTING: 更新记忆和状态
   - COMPLETED: Run 完成
   - FAILED: Run 失败
2. THE System SHALL 在每个阶段转换时记录日志
3. THE System SHALL 在每个阶段转换时更新 run 状态到数据库
4. THE System SHALL 支持 run 的暂停和恢复（通过 Hatchet Signal）
5. THE System SHALL 支持 run 的强制终止
6. THE System SHALL 在 run 完成时记录执行摘要到 Ledger
7. THE System SHALL 在 run 失败时记录错误详情到 Ledger
8. THE System SHALL 支持 run 的超时控制（默认 5 分钟）
9. WHEN run 超时时，THE System SHALL 自动终止并记录超时错误


### 需求 9：与 Hatchet 的集成

**用户故事：** 作为开发者，我希望 Agent Run 能够利用 Hatchet 的持久执行能力，保证崩溃恢复和重试。

#### 验收标准

1. THE System SHALL 将 Agent Run 注册为 Hatchet task
2. THE System SHALL 通过 Hatchet 接收触发事件（cron、schedule、webhook 等）
3. THE System SHALL 支持 Hatchet 的持久化 sleep（ctx.aio_sleep_for）
4. THE System SHALL 支持 Hatchet 的任务调度（schedule_task）
5. THE System SHALL 支持 Hatchet 的 cron 触发器
6. THE System SHALL 支持 Hatchet 的 Signal 机制（暂停/恢复/取消）
7. THE System SHALL 在 Hatchet task 失败时自动重试（可配置重试策略）
8. THE System SHALL 将 run 状态同步到 Hatchet Dashboard
9. THE System SHALL 支持 Hatchet 的并发控制（同一 Agent 的 run 串行执行）
10. THE System SHALL 隔离 Hatchet 集成代码到 owlclaw/integrations/hatchet.py

### 需求 10：与 litellm 的集成

**用户故事：** 作为开发者，我希望 Agent Runtime 能够统一调用多种 LLM 模型，而不依赖特定厂商。

#### 验收标准

1. THE System SHALL 使用 litellm 统一调用 LLM 模型
2. THE System SHALL 支持 litellm 的 100+ 模型（OpenAI、Anthropic、Google、Azure 等）
3. THE System SHALL 支持 litellm 的 function calling 接口
4. THE System SHALL 支持 litellm 的流式响应
5. THE System SHALL 支持 litellm 的重试和降级策略
6. THE System SHALL 通过 Governance Router 选择模型（基于 task_type）
7. THE System SHALL 将 litellm 调用集成到 Langfuse tracing
8. THE System SHALL 支持 litellm 的超时和取消
9. THE System SHALL 记录 litellm 调用的 token 使用量到 Ledger
10. THE System SHALL 隔离 litellm 集成代码到 owlclaw/integrations/llm.py

### 需求 11：与 Langfuse 的集成

**用户故事：** 作为系统管理员，我希望能够追踪和分析 Agent 的 LLM 调用，以便优化成本和性能。

#### 验收标准

1. THE System SHALL 集成 Langfuse Python SDK
2. THE System SHALL 为每次 Agent Run 创建 Langfuse trace
3. THE System SHALL 为每次 LLM 调用创建 Langfuse span
4. THE System SHALL 为每次工具调用创建 Langfuse span
5. THE System SHALL 在 Langfuse trace 中包含 Agent 身份信息
6. THE System SHALL 在 Langfuse trace 中包含 run 触发信息
7. THE System SHALL 在 Langfuse span 中包含 prompt 和 response
8. THE System SHALL 在 Langfuse span 中包含 token 使用量
9. THE System SHALL 在 Langfuse span 中包含执行耗时
10. THE System SHALL 支持 Langfuse 的异步上报（不阻塞 Agent Run）
11. THE System SHALL 隔离 Langfuse 集成代码到 owlclaw/integrations/langfuse.py

### 需求 12：错误处理和容错

**用户故事：** 作为系统管理员，我希望 Agent Runtime 能够优雅地处理各种错误，保证系统稳定性。

#### 验收标准

1. WHEN SOUL.md 或 IDENTITY.md 加载失败时，THE System SHALL 返回初始化错误
2. WHEN SKILL.md 格式错误时，THE System SHALL 记录警告并跳过该 Skill
3. WHEN 向量数据库连接失败时，THE System SHALL 降级到仅使用 MEMORY.md
4. WHEN LLM 调用失败时，THE System SHALL 根据重试策略重试或降级
5. WHEN 工具执行失败时，THE System SHALL 将错误信息返回给 LLM
6. WHEN Hatchet 任务失败时，THE System SHALL 根据重试策略重试
7. THE System SHALL 区分可重试错误和不可重试错误
8. THE System SHALL 为每种错误类型定义处理策略
9. THE System SHALL 记录所有错误到日志和 Ledger
10. THE System SHALL 支持错误的告警通知（可配置）

### 需求 13：性能和可扩展性

**用户故事：** 作为系统管理员，我希望 Agent Runtime 能够高效运行，支持大规模部署。

#### 验收标准

1. THE System SHALL 支持单个 Agent 实例每分钟 10+ 次 run
2. THE System SHALL 支持多个 Agent 实例并发运行
3. THE System SHALL 优化 Skills 加载（缓存 metadata，按需加载完整指令）
4. THE System SHALL 优化向量搜索（索引优化、查询缓存）
5. THE System SHALL 优化 LLM 调用（prompt 压缩、结果缓存）
6. THE System SHALL 限制单次 run 的最大内存使用（默认 512MB）
7. THE System SHALL 支持 run 的并发控制（同一 Agent 串行，不同 Agent 并行）
8. THE System SHALL 监控 run 的性能指标（延迟、成功率、错误率）
9. THE System SHALL 支持 run 的限流（防止资源耗尽）
10. THE System SHALL 支持水平扩展（多个 worker 实例）


### 需求 14：配置和可定制性

**用户故事：** 作为开发者，我希望能够灵活配置 Agent Runtime 的行为，适应不同的业务场景。

#### 验收标准

1. THE System SHALL 支持通过配置文件（owlclaw.yaml）配置 Agent Runtime
2. THE System SHALL 支持配置 LLM 模型选择（默认模型、降级链）
3. THE System SHALL 支持配置记忆系统（向量数据库类型、连接参数）
4. THE System SHALL 支持配置 token 限制（短期记忆、Skills 注入、总 prompt）
5. THE System SHALL 支持配置超时（LLM 调用、工具执行、run 总时长）
6. THE System SHALL 支持配置重试策略（最大重试次数、退避策略）
7. THE System SHALL 支持配置 Heartbeat 频率和检查逻辑
8. THE System SHALL 支持配置并发控制（最大并发 run 数）
9. THE System SHALL 支持配置日志级别和输出格式
10. THE System SHALL 支持配置的热重载（部分配置变更无需重启）
11. THE System SHALL 验证配置的合法性（启动时检查）

### 需求 15：测试和验证

**用户故事：** 作为开发者，我希望 Agent Runtime 有完善的测试覆盖，以便保证质量。

#### 验收标准

1. THE System SHALL 提供单元测试覆盖所有核心逻辑
2. THE System SHALL 提供集成测试验证与 Hatchet/litellm/Langfuse 的集成
3. THE System SHALL 提供端到端测试模拟完整的 Agent Run 流程
4. THE System SHALL 提供性能测试验证高负载下的表现
5. THE System SHALL 提供错误注入测试验证错误处理的健壮性
6. THE System SHALL 提供 mock 对象便于测试（mock LLM、mock 向量数据库）
7. THE System SHALL 提供测试夹具（fixture）便于测试数据准备
8. THE System SHALL 提供测试文档和示例
9. THE System SHALL 确保测试覆盖率 > 80%
10. THE System SHALL 在 CI/CD 中自动运行测试

### 需求 16：安全考虑

**用户故事：** 作为安全工程师，我希望 Agent Runtime 不会成为安全漏洞的入口。

#### 验收标准

1. THE System SHALL 对 SOUL.md 和 IDENTITY.md 的内容进行 sanitization
2. THE System SHALL 对 SKILL.md 的内容进行 sanitization
3. THE System SHALL 防止通过 Skills 注入恶意 prompt
4. THE System SHALL 限制 Agent 可访问的文件路径（沙箱）
5. THE System SHALL 验证工具调用的参数（类型、范围、格式）
6. THE System SHALL 记录所有 Agent Run 到审计日志
7. THE System SHALL 支持 Agent Run 的权限控制（企业版）
8. THE System SHALL 防止 Agent 访问其他 Agent 的数据
9. THE System SHALL 加密敏感数据（如 API keys、数据库密码）
10. THE System SHALL 支持 Agent Run 的速率限制（防止滥用）

## 非功能性需求

### 性能

- Agent Run 启动延迟 P95 < 1 秒（不包括 LLM 调用）
- LLM 调用延迟取决于模型（GPT-4: ~2-5 秒，Claude: ~1-3 秒）
- 向量搜索延迟 P95 < 200ms
- 支持单个 Agent 实例每分钟 10+ 次 run
- 支持多个 Agent 实例并发运行（水平扩展）

### 可靠性

- Agent Run 成功率 > 99%（不包括业务逻辑错误）
- 支持 Hatchet 的崩溃恢复和重试
- 支持 LLM 调用的降级策略
- 支持向量数据库的降级（降级到仅使用 MEMORY.md）
- 记录所有错误到日志和 Ledger

### 可维护性

- 代码模块化，职责清晰
- 集成组件隔离（Hatchet、litellm、Langfuse）
- 提供清晰的错误信息和日志
- 支持配置的热重载
- 提供完善的测试覆盖

### 可扩展性

- 支持添加新的触发器类型
- 支持添加新的向量数据库后端
- 支持添加新的 LLM 模型
- 支持自定义 Skills 加载逻辑
- 支持自定义治理过滤规则

## 依赖

- **owlclaw.integrations.hatchet** — 持久执行和任务调度
- **owlclaw.integrations.llm** — LLM 调用（litellm）
- **owlclaw.integrations.langfuse** — LLM 调用追踪
- **owlclaw.agent.tools** — Agent 内建工具
- **owlclaw.capabilities.registry** — 业务能力注册
- **owlclaw.capabilities.skills** — Skills 加载和管理
- **owlclaw.governance.visibility** — 工具可见性过滤
- **owlclaw.governance.ledger** — 执行记录
- **owlclaw.db** — 数据库访问（PostgreSQL）
- **向量数据库** — pgvector、Qdrant 等（业务应用配置）

## 约束

- Agent Runtime 必须遵循 Agent Skills 规范（agentskills.io）
- SOUL.md 和 IDENTITY.md 必须是 Markdown 格式
- SKILL.md 必须包含 YAML frontmatter
- 所有文件路径必须相对于应用目录
- Agent Run 必须是幂等的（相同输入产生相同输出，除了时间相关的决策）
- Agent Run 必须支持中断和恢复（通过 Hatchet）


## 验收测试场景

### 场景 1：Agent 启动并加载身份

```
GIVEN 应用目录包含 SOUL.md 和 IDENTITY.md
WHEN Agent Runtime 初始化
THEN Agent 成功加载角色定位和能力范围
AND system prompt 包含 SOUL.md 内容
AND system prompt 包含 IDENTITY.md 的能力摘要
```

### 场景 2：Agent 基于 Skills 理解业务能力

```
GIVEN 应用目录包含 capabilities/entry-monitor/SKILL.md
WHEN Agent Runtime 初始化
THEN Agent 加载 entry-monitor 的 metadata
AND WHEN Agent Run 启动时
THEN Agent 根据上下文加载 entry-monitor 的完整指令
AND system prompt 包含 SKILL.md 的使用指南
```

### 场景 3：Agent 通过 function calling 自主决策

```
GIVEN Agent Run 启动，触发事件为 "check entry opportunities"
WHEN Agent 看到可见工具列表（包括 check_entry_opportunity、query_state 等）
THEN Agent 通过 LLM function calling 选择先调用 query_state("market_state")
AND 获取市场状态后，Agent 选择调用 check_entry_opportunity
AND 发现机会后，Agent 选择调用 schedule_once(300, "review entry decision")
AND Agent 调用 log_decision 记录决策理由
AND Agent Run 完成
```

### 场景 4：Agent 记住并回忆经验

```
GIVEN Agent 在市场急跌后发现反弹信号准确
WHEN Agent 调用 remember("After sharp drop, rebound signals accurate within 2h", tags=["trading", "lesson"])
THEN 记忆被写入 MEMORY.md 和向量数据库
AND 下次市场急跌时，Agent 调用 recall("market crash recovery")
AND recall 返回之前的经验
AND Agent 基于经验做出更好的决策
```

### 场景 5：Heartbeat 机制节省成本

```
GIVEN Agent 配置了 Heartbeat 触发器（每 5 分钟）
WHEN Heartbeat 触发时，没有待处理事件
THEN Agent 跳过 LLM 调用，直接结束 run
AND Ledger 记录 "Heartbeat: no events"
AND WHEN Heartbeat 触发时，有新的 webhook 事件
THEN Agent 启动完整的 Agent Run（包括 LLM 调用）
```

### 场景 6：治理过滤限制工具可见性

```
GIVEN Agent 配置了 trading_hours_only 约束
WHEN 非交易时间 Agent Run 启动
THEN check_entry_opportunity 不在可见工具列表中
AND Agent 看不到该工具，无法调用
AND Agent 可能选择调用 schedule_once 等待交易时间
```

### 场景 7：Agent Run 崩溃恢复

```
GIVEN Agent Run 正在执行，已调用 2 个工具
WHEN 进程崩溃（如 OOM）
THEN Hatchet 自动重试该任务
AND Agent Run 从头开始（幂等性保证）
AND Agent 重新执行决策流程
AND 最终完成 run
```

### 场景 8：LLM 调用失败降级

```
GIVEN Agent 配置了 LLM 降级链：GPT-4 → Claude-3 → GPT-3.5
WHEN GPT-4 调用失败（如 rate limit）
THEN Agent Runtime 自动降级到 Claude-3
AND 继续执行 Agent Run
AND Ledger 记录降级事件
```

## 参考

- OwlClaw 架构文档 `docs/ARCHITECTURE_ANALYSIS.md` §5（Agent 运行时设计）
- Agent Skills 规范（agentskills.io）
- 业界 Agent 框架的 Agent 实现（SOUL.md、MEMORY.md、Skills）
- agent-tools spec（内建工具接口）
- litellm 文档（LLM 统一调用）
- Hatchet 文档（持久执行）
- Langfuse 文档（LLM 追踪）
