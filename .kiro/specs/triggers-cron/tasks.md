# 实现计划：Cron 触发器

## 文档联动

- requirements: `.kiro/specs/triggers-cron/requirements.md`
- design: `.kiro/specs/triggers-cron/design.md`
- tasks: `.kiro/specs/triggers-cron/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

本实现计划将 Cron 触发器功能分解为离散的、可执行的任务。该功能提供持久化的、Agent 驱动的 cron 调度能力，集成了 Hatchet、治理约束和 fallback 机制，支持从传统 cron 任务的渐进式迁移。

## 任务列表

- [x] 1. 建立核心数据模型和配置
  - 创建包含所有配置字段的 `CronTriggerConfig` 数据类
  - 创建用于执行跟踪的 `CronExecution` 数据类
  - 创建执行状态的 `ExecutionStatus` 枚举
  - 设置类型提示和验证
  - _需求: FR-1, FR-2_

- [x] 2. 实现 CronTriggerRegistry 核心功能
  - [x] 2.1 创建 CronTriggerRegistry 类并初始化
    - 实现带 app 引用的 `__init__` 方法
    - 初始化内部触发器存储字典
    - 初始化 Hatchet workflow 存储
    - _需求: FR-2_
  
  - [x] 2.2 实现 cron 表达式验证
    - 使用 croniter 库添加 `_validate_cron_expression` 方法
    - 验证 5 字段 cron 格式
    - 支持特殊字符 (*, , - /)
    - 为无效表达式返回清晰的错误消息
    - _需求: FR-1_
  
  - [x]* 2.3 编写 cron 表达式验证的单元测试
    - 测试有效表达式（每小时、每天、每周模式）
    - 测试无效表达式（错误格式、超出范围）
    - 测试特殊字符和范围
    - _需求: FR-1_
  
  - [x] 2.4 实现触发器注册方法
    - 创建接受 event_name、expression、focus、fallback 的 `register` 方法
    - 验证 event_name 唯一性
    - 验证 cron 表达式
    - 创建 CronTriggerConfig 实例
    - 在注册表中存储配置
    - 添加注册的结构化日志
    - _需求: FR-2_
  
  - [x] 2.5 实现触发器查询方法
    - 创建 `get_trigger(event_name)` 方法
    - 创建 `list_triggers()` 方法
    - 返回适当的类型并处理缺失的触发器
    - _需求: FR-10_

- [x] 3. 实现 Hatchet workflow 集成
  - [x] 3.1 创建动态 Hatchet workflow 生成
    - 实现 `start(hatchet_client, agent_runtime, ledger)` 方法
    - 使用 hatchet_client.task(name, cron) 注册每个触发器
    - 将 workflow 名称设置为 `cron_{event_name}`
    - closure 正确捕获 config/agent_runtime/ledger/tenant_id
    - _需求: FR-3_
  
  - [x] 3.2 在 workflow 中实现 trigger_agent 步骤
    - 实现 `_run_cron` 方法（Hatchet task handler）
    - 使用 UUID 和时间戳创建 CronExecution 记录
    - 将初始状态设置为 PENDING
    - 构建包含类型、表达式、focus 的触发上下文
    - 使用 try/except/finally 添加错误处理和 Ledger 记录
    - _需求: FR-3, FR-4_
  
  - [x] 3.3 在 workflow 中实现治理检查
    - 实现 `_check_governance` 方法
    - 检查相对于上次执行的冷却时间（via Ledger）
    - 检查每日运行次数限制（via Ledger）
    - 检查每日成本限制（via Ledger）
    - 返回 (passed, reason) 元组
    - 无 Ledger 时 fail-open（跳过检查）
    - _需求: FR-6_
  
  - [x] 3.4 实现 Agent vs Fallback 决策逻辑
    - 实现 `_should_use_agent` 静态方法
    - 使用 migration_weight 进行概率选择（random.random）
    - 支持渐进式迁移（0.0 到 1.0）
    - 设置 execution.decision_mode
    - _需求: FR-8, FR-9_
  
  - [x] 3.5 实现 Agent 执行路径
    - 实现 `_execute_agent` 方法
    - 调用 agent_runtime.trigger_event(event_name, focus, payload)
    - 将 agent_run_id、llm_calls 记录到 execution
    - _需求: FR-4_
  
  - [x] 3.6 实现 Fallback 执行路径
    - 实现 `_execute_fallback` 方法
    - 检查 fallback_handler 是否存在
    - 支持 async/sync fallback handler
    - 将执行状态设置为 FALLBACK
    - _需求: FR-8_
  
  - [x] 3.7 实现失败处理
    - 实现 `_handle_failure` 方法
    - 检查 fallback_strategy (on_failure/always/never)
    - 如果配置了则尝试 fallback 执行
    - fallback 失败时记录日志不抛出
    - _需求: FR-8_
  
  - [x]* 3.8 编写 workflow 执行的集成测试
    - 测试成功的 Agent 执行（agent_run_id 记录）
    - 测试 Agent 失败时的 fallback（on_failure strategy）
    - 测试治理约束执行（cooldown/daily_runs/daily_cost）
    - 测试执行记录到 Ledger（成功/失败两路径）
    - 测试 Hatchet 注册（task 数量/表达式/workflows dict）
    - _需求: FR-3, FR-4, FR-6, FR-8_

- [x] 4. 实现 @app.cron 装饰器 API
  - [x] 4.1 向 OwlClawApp 添加 cron 装饰器
    - 在 OwlClawApp 类中创建 `cron` 方法
    - 接受 expression、event_name、focus、description、fallback 参数
    - 接受 **kwargs 用于治理和重试配置
    - 返回装饰器函数
    - _需求: FR-2_
  
  - [x] 4.2 实现装饰器逻辑
    - 如果未提供，使用函数名作为默认 event_name
    - 如果未指定，使用被装饰的函数作为默认 fallback
    - 使用所有参数调用 registry.register
    - 使用 @wraps 保留函数元数据
    - 返回包装的异步函数
    - _需求: FR-2_
  
  - [x] 4.3 向 OwlClawApp 添加 cron_registry 属性
    - 在 __init__ 中初始化 CronTriggerRegistry
    - 作为属性公开以供直接访问
    - _需求: FR-2_
  
  - [x]* 4.4 编写装饰器的单元测试
    - 测试基本装饰器用法
    - 测试显式 event_name
    - 测试 focus 参数
    - 测试治理参数
    - 测试函数元数据保留
    - _需求: FR-2_

- [x] 5. 检查点 - 确保核心注册和 workflow 创建正常工作
  - 验证可以通过装饰器注册触发器
  - 验证 Hatchet workflows 正确创建
  - 验证 cron 表达式得到验证
  - _验收_：68 个 triggers + app 测试全通过（2026-02-21）

- [ ] 6. 实现 Focus 和 Skills 集成
  - [ ] 6.1 创建 FocusManager 类
    - 使用 SkillsManager 依赖实现 `__init__`
    - 创建 `load_skills_for_focus` 方法
    - 如果 focus 为 None 则加载所有 skills
    - 如果提供了 focus 则按 focus 标签过滤 skills
    - _需求: FR-5_
  
  - [ ] 6.2 实现 skill 匹配逻辑
    - 创建 `_skill_matches_focus` 方法
    - 从 skill 元数据/frontmatter 读取 focus 标签
    - 支持字符串和列表 focus 值
    - 返回布尔匹配结果
    - _需求: FR-5_
  
  - [ ] 6.3 实现 Agent prompt 构建
    - 创建 `build_agent_prompt` 方法
    - 如果指定则在 prompt 中包含当前 focus
    - 列出可用 skills 及其名称和描述
    - 格式化 prompt 供 Agent 使用
    - _需求: FR-5_
  
  - [ ]* 6.4 编写 FocusManager 的单元测试
    - 测试 focus 为 None 时加载所有 skills
    - 测试按 focus 标签过滤 skills
    - 测试 skill 匹配逻辑
    - 测试有无 focus 的 prompt 构建
    - _需求: FR-5_

- [ ] 7. 实现治理集成
  - [ ] 7.1 创建 CronGovernance 类
    - 使用 GovernanceManager 和 Ledger 依赖实现 `__init__`
    - 设置约束检查基础设施
    - _需求: FR-6_
  
  - [ ] 7.2 实现约束检查方法
    - 创建返回 (passed, reason) 的 `check_constraints` 方法
    - 通过 `_get_last_successful_execution` 实现冷却时间检查
    - 通过 `_count_today_executions` 实现每日运行次数检查
    - 通过 `_sum_today_cost` 实现每日成本检查
    - 通过 `_check_circuit_breaker` 实现熔断器检查
    - 使用结果更新 execution.governance_checks
    - _需求: FR-6_
  
  - [ ] 7.3 实现 Ledger 记录
    - 创建 `record_execution` 方法
    - 将 event_type 记录为 "cron_execution"
    - 包含 execution_id、status、duration、cost、llm_calls
    - 包含 governance_checks 和 error_message
    - 使用结构化数据格式
    - _需求: FR-7_
  
  - [ ] 7.4 实现熔断器逻辑
    - 创建 `update_circuit_breaker` 方法
    - 获取最近 N 次执行（默认 10）
    - 计算失败率
    - 如果 failure_rate > 阈值（默认 0.5）则打开熔断器
    - 在 Redis/DB 中存储熔断器状态
    - 熔断器打开时发送告警
    - _需求: FR-6_
  
  - [ ] 7.5 实现 Ledger 查询辅助方法
    - 创建 `_get_last_successful_execution` 方法
    - 创建 `_count_today_executions` 方法
    - 创建 `_sum_today_cost` 方法
    - 创建 `_get_recent_executions` 方法
    - 正确处理时间范围和过滤
    - _需求: FR-7_
  
  - [ ]* 7.6 编写治理的单元测试
    - 测试冷却约束检查
    - 测试每日运行限制检查
    - 测试每日成本限制检查
    - 测试熔断器逻辑
    - 测试 Ledger 记录
    - _需求: FR-6, FR-7_

- [ ] 8. 实现任务管理操作
  - [x] 8.1 实现暂停/恢复功能
    - [x] 创建 `pause_trigger(event_name)` 方法
    - [x] 创建 `resume_trigger(event_name)` 方法
    - [x] 更新 config.enabled 标志
    - [ ] 与 Hatchet API 集成以暂停/恢复 workflows（当前通过 config.enabled 在 _run_cron 中跳过）
    - [ ] 将暂停/恢复操作记录到 Ledger
    - _需求: FR-11_
  
- [x] 8.2 实现手动触发功能
  - [x] 创建 `trigger_now(event_name, **kwargs)` 方法
  - [x] 直接执行 workflow（调用 Hatchet run_task_now）
  - [x] 支持通过 kwargs 传递额外上下文
  - [x] 将手动触发记录到 Ledger
  - _需求: FR-12_
  
  - [x] 8.3 实现状态查询方法
    - [x] 创建 `get_trigger_status(event_name)` 方法
    - [x] 返回触发器配置、启用状态、下次执行时间（croniter）
    - [ ] 从最近执行计算成功率
    - [ ] 计算平均执行时长
    - _需求: FR-10_
  
  - [x] 8.4 实现执行历史查询
    - [x] 创建 `get_execution_history(event_name, limit, tenant_id)` 方法
    - [x] 查询 Ledger 中的 cron_execution 事件（capability_name=event_name）
    - [x] 将 LedgerRecord 转为 dict 返回（run_id, status, created_at 等）
    - [x] 使用 limit 参数支持分页（1-100）
    - [x] 按 created_at 降序排序
    - _需求: FR-10_
  
  - [ ]* 8.5 编写任务管理的集成测试
    - 测试暂停和恢复操作
    - 测试手动触发执行
    - 测试带指标的状态查询
    - 测试执行历史检索
    - _需求: FR-10, FR-11, FR-12_

- [ ] 9. 检查点 - 确保治理和管理功能正常工作
  - 验证治理约束得到执行
  - 验证暂停/恢复功能
  - 验证手动触发工作
  - 验证执行历史被记录
  - 如有问题请询问用户

- [ ] 10. 实现监控和可观测性
  - [ ] 10.1 使用 Prometheus 指标创建 CronMetrics 类
    - 定义带标签的 executions_total Counter
    - 定义 execution_duration_seconds Histogram
    - 定义 trigger_delay_seconds Histogram
    - 定义 execution_cost_usd Histogram
    - 定义 llm_calls_total Counter
    - 定义 active_tasks Gauge
    - 定义 circuit_breaker_open Gauge
    - _需求: NFR-6_
  
  - [ ] 10.2 实现指标记录方法
    - 创建 `record_execution` 类方法
    - 按状态和 decision_mode 记录执行次数
    - 记录执行时长
    - 记录执行成本
    - 记录 LLM 调用次数
    - 创建用于延迟跟踪的 `record_trigger_delay` 方法
    - _需求: NFR-6_
  
  - [ ] 10.3 创建用于结构化日志的 CronLogger
    - 实现触发器注册的 `log_registration`
    - 实现 cron 触发事件的 `log_trigger`
    - 实现执行开始的 `log_execution_start`
    - 实现成功完成的 `log_execution_complete`
    - 实现失败的 `log_execution_failed`
    - 实现跳过执行的 `log_governance_skip`
    - 实现熔断器事件的 `log_circuit_breaker_open`
    - 使用 structlog 进行结构化日志记录
    - _需求: NFR-5_
  
  - [ ] 10.4 实现健康检查端点
    - 创建 CronHealthCheck 类
    - 实现返回状态字典的 `check_health` 方法
    - 检查 Hatchet 连接健康状况
    - 检查触发器状态（启用/禁用计数）
    - 检查熔断器状态
    - 返回 "healthy"、"degraded" 或 "unhealthy" 状态
    - _需求: NFR-5_
  
  - [ ]* 10.5 编写监控测试
    - 测试指标记录
    - 测试结构化日志输出
    - 测试健康检查响应
    - _需求: NFR-5, NFR-6_

- [ ] 11. 实现错误处理和重试逻辑
  - [ ] 11.1 创建 RetryStrategy 类
    - 实现 `should_retry` 静态方法
    - 检查错误类型（不重试 ValueError、TypeError）
    - 检查重试次数与 max_retries
    - 检查 retry_on_failure 标志
    - 返回布尔决策
    - _需求: FR-8_
  
  - [ ] 11.2 实现重试延迟计算
    - 创建 `calculate_delay` 静态方法
    - 实现指数退避：base_delay * (2 ** retry_count)
    - 限制最大延迟
    - _需求: FR-8_
  
  - [ ] 11.3 创建 CircuitBreaker 类
    - 使用 failure_threshold 和 window_size 实现 `__init__`
    - 创建 `check` 方法评估熔断器状态
    - 创建 `open` 方法打开熔断器
    - 创建 `close` 方法关闭熔断器
    - 与 Redis/DB 集成以实现状态持久化
    - _需求: FR-6_
  
  - [ ] 11.4 创建 ErrorNotifier 类
    - 实现 `notify_failure` 方法
    - 创建 `_should_notify` 逻辑（在第 1、3、5 次失败时通知）
    - 创建通知内容的 `_build_message`
    - 支持多个通知渠道（邮件、Slack）
    - _需求: FR-8_
  
  - [ ]* 11.5 编写错误处理测试
    - 测试重试决策逻辑
    - 测试指数退避计算
    - 测试熔断器状态转换
    - 测试通知触发
    - _需求: FR-6, FR-8_

- [ ] 12. 实现性能优化
  - [ ] 12.1 创建 ConcurrencyController
    - 使用 asyncio.Semaphore 实现并发限制
    - 创建 `execute_with_limit` 方法
    - 在字典中跟踪活动任务
    - 实现 `get_active_count` 方法
    - 实现用于优雅关闭的 `wait_all` 方法
    - _需求: NFR-2_
  
  - [ ] 12.2 创建 PriorityScheduler
    - 使用 heapq 实现优先级队列
    - 创建 PrioritizedTask 数据类
    - 实现带优先级的 `schedule` 方法
    - 实现 `execute_next` 方法
    - 使用 asyncio.Lock 实现线程安全
    - _需求: NFR-2_
  
  - [ ] 12.3 创建用于性能的 CronCache
    - 实现执行记录缓存
    - 实现带 TTL 的统计缓存
    - 使用 @lru_cache 进行 next_trigger_time 计算
    - 实现缓存失效逻辑
    - _需求: NFR-1_
  
  - [ ] 12.4 实现批量操作
    - 创建 BatchOperations 类
    - 实现用于批量 Ledger 写入的 `batch_record_executions`
    - 实现用于高效查询的 `batch_query_executions`
    - 使用可配置的 batch_size（默认 100）
    - _需求: NFR-1_

- [ ] 13. 添加配置和部署支持
  - [ ] 13.1 创建配置模式
    - 定义 Hatchet 连接的环境变量
    - 定义 cron 设置的环境变量
    - 定义治理默认值的环境变量
    - 创建 owlclaw.yaml 配置文件模式
    - 支持治理、重试、通知的嵌套配置
    - _需求: 所有 NFRs_
  
  - [ ] 13.2 实现配置加载
    - 从环境变量加载
    - 从 YAML 配置文件加载
    - 按优先级合并配置
    - 验证配置值
    - _需求: 所有 NFRs_
  
  - [ ] 13.3 创建 Docker 部署文件
    - 为 OwlClaw 应用创建 Dockerfile
    - 创建包含 OwlClaw、Hatchet、PostgreSQL 的 docker-compose.yml
    - 添加 Prometheus 服务用于指标
    - 配置健康检查和重启策略
    - _需求: NFR-3_
  
  - [ ] 13.4 创建 Kubernetes 部署清单
    - 创建带副本的 Deployment 清单
    - 创建指标端点的 Service 清单
    - 添加 Prometheus 抓取注解
    - 配置资源请求和限制
    - 添加存活和就绪探针
    - _需求: NFR-3_

- [ ] 14. 创建文档和示例
  - [ ] 14.1 编写 API 文档
    - 记录带所有参数的 @app.cron 装饰器
    - 记录 CronTriggerRegistry 公共方法
    - 记录配置选项
    - 为所有公共类和方法添加文档字符串
    - _需求: 所有 FRs_
  
  - [ ] 14.2 创建使用示例
    - 创建每小时库存检查示例
    - 创建交易日早盘决策示例
    - 创建每日报告生成示例
    - 创建数据清理任务示例
    - 创建 focus 和 Skills 集成示例
    - 创建治理约束示例
    - _需求: 所有 FRs_
  
  - [ ] 14.3 编写迁移指南
    - 记录现有 cron 任务的评估
    - 记录渐进式迁移策略
    - 记录 fallback 配置
    - 记录回滚程序
    - 包含迁移检查清单
    - _需求: FR-9_
  
  - [ ] 14.4 创建故障排查指南
    - 记录常见问题和解决方案
    - 记录调试工具和技术
    - 记录健康检查程序
    - 包含日志分析示例
    - _需求: 所有 NFRs_

- [ ] 15. 最终集成和测试
  - [ ]* 15.1 编写端到端测试
    - 测试从注册到执行的完整工作流
    - 测试 Agent 使用 Skills 的决策
    - 测试 Agent 失败时的 fallback
    - 测试治理约束执行
    - 测试熔断器触发
    - 测试手动触发和暂停/恢复
    - _需求: 所有 FRs_
  
  - [ ]* 15.2 编写性能测试
    - 测试触发延迟（P95 < 5s，P99 < 10s）
    - 测试并发执行（100+ 任务）
    - 测试重启后的系统恢复
    - 测试 Hatchet 故障转移场景
    - _需求: NFR-1, NFR-2, NFR-3_
  
  - [ ] 15.3 与现有 OwlClaw 组件集成
    - 与 Agent Runtime 集成以实现 trigger_event
    - 与 Skills 系统集成以实现基于 focus 的加载
    - 与 Governance 层集成以实现约束
    - 与 Ledger 集成以实现执行记录
    - 与 Hatchet 客户端集成以实现 workflow 注册
    - _需求: 所有 FRs_
  
  - [ ] 15.4 更新 OwlClawApp 初始化
    - 在应用启动时初始化 CronTriggerRegistry
    - 在 app.start() 期间注册所有 cron 触发器
    - 为活动任务实现优雅关闭
    - 向应用添加健康检查端点
    - _需求: 所有 FRs_

- [ ] 16. 最终检查点 - 完整系统验证
  - 运行所有单元测试并验证覆盖率 ≥ 80%
  - 运行所有集成测试
  - 使用真实 Hatchet 实例运行端到端测试
  - 验证性能要求（触发延迟、并发能力）
  - 验证所有文档完整
  - 请求用户进行最终审查

## 注意事项

- 标有 `*` 的任务为测试重点标记，不代表可跳过；发布前需完成并通过验收
- 每个任务都引用特定需求以实现可追溯性
- 实现遵循设计文档架构
- 通过检查点关注增量验证
- 治理集成对生产就绪至关重要
- 监控和可观测性对运营卓越至关重要
- 迁移支持使得能够从传统 cron 逐步采用
