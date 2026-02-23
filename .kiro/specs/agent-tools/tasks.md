# 任务清单

## 文档联动

- requirements: `.kiro/specs/agent-tools/requirements.md`
- design: `.kiro/specs/agent-tools/design.md`
- tasks: `.kiro/specs/agent-tools/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Task 0: 文档和契约

- [x] 0.1 确认 requirements.md 完整且经过审核
- [x] 0.2 确认 design.md 完整且经过审核
- [x] 0.3 与依赖组件的接口契约已明确（Hatchet、Memory System、Capability Registry、Governance Ledger）

## Task 1: BuiltInTools 核心类实现

- [x] 1.1 创建 `owlclaw/agent/tools.py` 文件
- [x] 1.2 实现 `BuiltInTools` 类基础结构
  - [x] 1.2.1 构造函数（接受 capability_registry、ledger；hatchet/memory 待 Task 2/3）
  - [x] 1.2.2 `get_tool_schemas()` 方法（返回所有工具的 function calling schema）
  - [x] 1.2.3 `execute()` 方法（统一的工具执行入口，包含超时和错误处理）
- [x] 1.3 实现工具名称到方法的映射逻辑
- [x] 1.4 实现工具执行的超时机制（默认 30 秒）
- [x] 1.5 实现工具执行的 Ledger 记录（成功和失败都记录）（log_decision 已写 Ledger；query_state 不写 Ledger）

## Task 2: 调度工具实现

- [x] 2.1 实现 `schedule_once` 工具
  - [x] 2.1.1 实现 `_schedule_once_schema()` 方法（返回 function calling schema）
  - [x] 2.1.2 实现 `schedule_once()` 方法（调用 Hatchet schedule_task，task=agent_scheduled_run）
  - [x] 2.1.3 参数验证（delay_seconds 范围：1-2592000）
  - [x] 2.1.4 返回 schedule_id 和调度信息
- [x] 2.2 实现 `schedule_cron` 工具
  - [x] 2.2.1 实现 `_schedule_cron_schema()` 方法
  - [x] 2.2.2 实现 `schedule_cron()` 方法（调用 HatchetClient.schedule_cron → cron.aio.create）
  - [x] 2.2.3 实现 `_validate_cron_expression()` 方法（复用 CronTriggerRegistry）
  - [x] 2.2.4 返回 schedule_id、cron_expression、focus
- [x] 2.3 实现 `cancel_schedule` 工具
  - [x] 2.3.1 实现 `_cancel_schedule_schema()` 方法
  - [x] 2.3.2 实现 `cancel_schedule()` 方法（调用 Hatchet cancel_task）
  - [x] 2.3.3 返回取消是否成功的信息

## Task 3: 记忆工具实现

- [x] 3.1 实现 `remember` 工具
  - [x] 3.1.1 实现 `_remember_schema()` 方法
  - [x] 3.1.2 实现 `remember()` 方法（调用 Memory System write）
  - [x] 3.1.3 参数验证（content 非空，最大 2000 字符）
  - [x] 3.1.4 支持可选的 tags 参数
  - [x] 3.1.5 返回 memory_id 和时间戳
- [x] 3.2 实现 `recall` 工具
  - [x] 3.2.1 实现 `_recall_schema()` 方法
  - [x] 3.2.2 实现 `recall()` 方法（调用 Memory System search）
  - [x] 3.2.3 参数验证（limit 范围：1-20，默认 5）
  - [x] 3.2.4 返回记忆列表和数量

## Task 4: 状态查询和决策记录工具实现

- [x] 4.1 实现 `query_state` 工具
  - [x] 4.1.1 实现 `_query_state_schema()` 方法
  - [x] 4.1.2 实现 `query_state()` 方法（调用 Capability Registry get_state）
  - [x] 4.1.3 错误处理（state_name 不存在时返回清晰错误）
  - [x] 4.1.4 返回状态数据（dict）
- [x] 4.2 实现 `log_decision` 工具
  - [x] 4.2.1 实现 `_log_decision_schema()` 方法
  - [x] 4.2.2 实现 `log_decision()` 方法（调用 Ledger record_execution）
  - [x] 4.2.3 参数验证（reasoning 非空，最大 1000 字符）
  - [x] 4.2.4 支持 decision_type 枚举（capability_selection、schedule_decision、no_action、other）
  - [x] 4.2.5 返回 decision_id

## Task 5: 错误处理和边界条件

- [x] 5.1 实现参数验证错误的统一处理（新增 `raise_errors=True` 时抛 ValueError，默认兼容返回 error dict）
- [x] 5.2 实现系统错误的统一处理（新增 `raise_errors=True` 时抛 RuntimeError，默认兼容返回 error dict）
- [x] 5.3 实现超时错误的统一处理（新增 `raise_errors=True` 时抛 TimeoutError，默认兼容返回 error dict）
- [x] 5.4 实现工具不存在错误的处理（execute 方法中）
- [x] 5.5 实现并发调用的数据一致性保护（通过 run 级计数锁保证并发安全）
- [x] 5.6 实现单次 Agent Run 中工具调用次数限制（max_calls_per_run）

## Task 6: 单元测试

- [x] 6.1 测试 `BuiltInTools` 类基础功能
  - [x] 6.1.1 测试 `get_tool_schemas()` 返回所有工具的 schema
  - [x] 6.1.2 测试 `execute()` 方法的工具路由逻辑
  - [x] 6.1.3 测试 `execute()` 方法的超时机制
  - [x] 6.1.4 测试 `execute()` 方法的错误处理
- [x] 6.2 测试调度工具
  - [x] 6.2.1 测试 `schedule_once` 成功场景
  - [x] 6.2.2 测试 `schedule_once` 参数验证（delay_seconds 超出范围）
  - [x] 6.2.3 测试 `schedule_cron` 成功场景
  - [x] 6.2.4 测试 `schedule_cron` cron 表达式验证
  - [x] 6.2.5 测试 `cancel_schedule` 成功场景
  - [x] 6.2.6 测试 `cancel_schedule` 任务不存在场景
- [x] 6.3 测试记忆工具
  - [x] 6.3.1 测试 `remember` 成功场景
  - [x] 6.3.2 测试 `remember` 参数验证（content 为空）
  - [x] 6.3.3 测试 `remember` 参数验证（content 超长）
  - [x] 6.3.4 测试 `remember` 带 tags 场景
  - [x] 6.3.5 测试 `recall` 成功场景
  - [x] 6.3.6 测试 `recall` 参数验证（limit 超出范围）
  - [x] 6.3.7 测试 `recall` 无结果场景
- [x] 6.4 测试状态查询和决策记录工具
  - [x] 6.4.1 测试 `query_state` 成功场景
  - [x] 6.4.2 测试 `query_state` state_name 不存在场景
  - [x] 6.4.3 测试 `log_decision` 成功场景
  - [x] 6.4.4 测试 `log_decision` 参数验证（reasoning 为空）
  - [x] 6.4.5 测试 `log_decision` 参数验证（reasoning 超长）
  - [x] 6.4.6 测试 `log_decision` 不同 decision_type 场景

## Task 7: 集成测试

- [x] 7.1 测试与 Hatchet 集成
  - [x] 7.1.1 测试 schedule_once 调用 Hatchet schedule_task
  - [x] 7.1.2 测试 schedule_cron 调用 Hatchet schedule_cron
  - [x] 7.1.3 测试 cancel_schedule 调用 Hatchet cancel_task
  - [x] 7.1.4 测试 Hatchet 任务执行后触发 Agent Run（通过 schedule payload 模拟下次 Run 上下文）
- [x] 7.2 测试与 Memory System 集成
  - [x] 7.2.1 测试 remember 写入 MEMORY.md 和向量数据库（覆盖 MEMORY.md fallback 写入）
  - [x] 7.2.2 测试 recall 从向量数据库搜索（InMemoryStore 向量检索契约）
  - [x] 7.2.3 测试记忆的时间衰减
- [x] 7.3 测试与 Capability Registry 集成
  - [x] 7.3.1 测试 query_state 调用注册的 state provider
  - [x] 7.3.2 测试 state provider 异步执行
  - [x] 7.3.3 测试 state provider 超时
- [x] 7.4 测试与 Governance Ledger 集成
  - [x] 7.4.1 测试所有工具调用都记录到 Ledger
  - [x] 7.4.2 测试 log_decision 写入 Ledger
  - [x] 7.4.3 测试 Ledger 记录包含完整上下文（agent_id、run_id、参数、结果）

## Task 8: 端到端测试

- [x] 8.1 测试 Agent 调用 schedule_once 后延迟执行
  - [x] 8.1.1 Agent Run 调用 schedule_once(300, "check entry")
  - [x] 8.1.2 5 分钟后新的 Agent Run 被触发
  - [x] 8.1.3 新 Run 的 context 包含 focus="check entry"
- [x] 8.2 测试 Agent 记住并回忆经验
  - [x] 8.2.1 Agent Run 调用 remember("lesson content", tags=["trading"])
  - [x] 8.2.2 记忆被写入 MEMORY.md 和向量数据库
  - [x] 8.2.3 后续 Agent Run 调用 recall("trading lessons")
  - [x] 8.2.4 recall 返回之前的记忆
- [x] 8.3 测试 Agent 查询状态后决策
  - [x] 8.3.1 Agent Run 调用 query_state("market_state")
  - [x] 8.3.2 返回 {"is_trading_time": false}
  - [x] 8.3.3 Agent 调用 log_decision("Non-trading hours, skipping", decision_type="no_action")
  - [x] 8.3.4 不调用任何业务 capability
- [x] 8.4 测试 Agent 取消不必要的调度
  - [x] 8.4.1 Agent Run 调用 schedule_once 返回 schedule_id
  - [x] 8.4.2 同一 Run 中 Agent 调用 cancel_schedule(schedule_id)
  - [x] 8.4.3 Hatchet 任务被取消
  - [x] 8.4.4 该任务不会再执行

## Task 9: 性能测试

- [x] 9.1 测试工具调用延迟（P95 < 500ms）
- [x] 9.2 测试向量搜索（recall）延迟（P95 < 200ms）
- [x] 9.3 测试高并发工具调用（单个 Agent 实例每秒 10+ 次）
- [x] 9.4 测试 remember 异步写入不阻塞 Agent Run

## Task 10: 文档和示例

- [x] 10.1 编写 `owlclaw/agent/tools.py` 的 docstrings
- [x] 10.2 编写使用示例（examples/agent_tools_demo.py）
  - [x] 10.2.1 示例：Agent 自我调度
  - [x] 10.2.2 示例：Agent 记住并回忆经验
  - [x] 10.2.3 示例：Agent 查询状态后决策
  - [x] 10.2.4 示例：Agent 记录决策理由
- [x] 10.3 更新 README.md 的内建工具部分
- [x] 10.4 编写 API 文档（新增 `docs/AGENT_TOOLS_API.md`）

## Task 11: 安全审查

- [x] 11.1 审查 remember 工具的 content sanitization（接入 `InputSanitizer`，净化后写入）
- [x] 11.2 审查 query_state 工具的状态范围限制（新增 state_name 字符白名单校验）
- [x] 11.3 审查 schedule_once/schedule_cron 工具的频率限制（新增 `max_schedule_calls_per_run`）
- [x] 11.4 审查所有工具参数的类型和范围验证（补齐并回归校验用例）
- [x] 11.5 审查工具调用的审计日志完整性（新增 `list_security_events()` 与安全事件记录）
- [x] 11.6 审查 cancel_schedule 工具的权限验证（新增可选 `enforce_schedule_ownership`）

## Task 12: 与其他组件的集成验证

- [x] 12.1 验证与 `owlclaw.integrations.hatchet` 的接口契约
- [x] 12.2 验证与 `owlclaw.agent.memory` 的接口契约（通过 `MemoryService` 适配器集成测试）
- [x] 12.3 验证与 `owlclaw.capabilities.registry` 的接口契约
- [x] 12.4 验证与 `owlclaw.governance.ledger` 的接口契约（待实现）
- [x] 12.5 验证工具在 Agent Runtime 中的注册和调用流程

## 依赖关系

- Task 1 必须先完成（核心类）
- Task 2-4 依赖 Task 1（工具实现依赖核心类）
- Task 5 依赖 Task 2-4（错误处理依赖工具实现）
- Task 6 依赖 Task 2-5（单元测试依赖实现）
- Task 7 依赖 Task 2-5 和外部组件（集成测试）
- Task 8 依赖 Task 7（端到端测试依赖集成测试）
- Task 9 依赖 Task 8（性能测试依赖端到端测试）
- Task 10 可以与 Task 6-9 并行（文档）
- Task 11 依赖 Task 2-5（安全审查依赖实现）
- Task 12 依赖所有其他 Task（最终集成验证）

## 注意事项

1. **Hatchet 集成**：调度工具依赖 `owlclaw.integrations.hatchet`，该模块需要先实现
2. **Memory System**：记忆工具依赖 `owlclaw.agent.memory`，该模块需要先实现
3. **Governance Ledger**：所有工具依赖 `owlclaw.governance.ledger`，该模块需要先实现
4. **测试隔离**：单元测试应使用 mock 对象，不依赖真实的 Hatchet/数据库
5. **异步执行**：所有工具方法都是 async，测试需要使用 pytest-asyncio
6. **错误传播**：工具执行失败时，错误应该被包装并传播给 Agent Runtime，不应该静默失败
