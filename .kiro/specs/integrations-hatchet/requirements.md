# Requirements Document

## Introduction

本文档定义 OwlClaw 与 Hatchet（MIT 许可证）的集成需求。Hatchet 为 OwlClaw 提供持久化任务执行、Cron 调度、延迟执行和自我调度能力。集成方式采用隔离设计，所有 Hatchet 调用集中在 `owlclaw/integrations/hatchet.py` 中。

## Glossary

- **Hatchet**: MIT 许可证的持久化任务队列和调度系统，支持崩溃恢复、重试、Cron 调度
- **Hatchet_Client**: OwlClaw 对 Hatchet Python SDK 的封装客户端
- **Durable_Task**: 通过 Hatchet 持久化的任务，支持崩溃恢复和重试
- **Hatchet_Server**: Hatchet 的服务端组件（Go 实现）
- **Worker**: 执行 Hatchet 任务的工作进程
- **Workflow**: Hatchet 中的工作流定义，包含一个或多个步骤
- **Step**: Workflow 中的单个执行单元
- **Cron_Trigger**: Hatchet 内建的定时触发器
- **Schedule_Task**: 延迟执行或自我调度的任务
- **Context**: Hatchet 任务执行时的上下文对象，提供 sleep、schedule 等能力
- **OwlClaw_Config**: OwlClaw 的配置系统（owlclaw.yaml）
- **PostgreSQL**: 复用宿主已有实例，database 级隔离；Hatchet 使用独立的 **hatchet** database，OwlClaw 业务使用 **owlclaw** database。详见 `docs/DATABASE_ARCHITECTURE.md`。

## Requirements

### Requirement 1: Hatchet 客户端初始化和连接管理

**User Story:** 作为 OwlClaw 开发者，我希望能够初始化 Hatchet 客户端并管理连接，以便 OwlClaw 能够与 Hatchet Server 通信。

#### Acceptance Criteria

1. WHEN OwlClaw 启动时，THE Hatchet_Client SHALL 从 OwlClaw_Config 读取 Hatchet 连接配置
2. WHEN 配置包含有效的 Hatchet Server 地址和认证信息时，THE Hatchet_Client SHALL 建立与 Hatchet_Server 的连接
3. WHEN 连接失败时，THE Hatchet_Client SHALL 记录错误并抛出异常
4. WHEN 连接成功时，THE Hatchet_Client SHALL 返回可用的客户端实例
5. WHEN OwlClaw 关闭时，THE Hatchet_Client SHALL 优雅地关闭连接并清理资源

### Requirement 2: 持久化任务装饰器

**User Story:** 作为 OwlClaw 开发者，我希望能够使用装饰器将 Python 函数标记为持久化任务，以便这些任务支持崩溃恢复和重试。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 提供 `@hatchet.task()` 装饰器用于标记持久化任务
2. WHEN 函数被 `@hatchet.task()` 装饰时，THE Hatchet_Client SHALL 将该函数注册为 Hatchet Workflow
3. WHEN 装饰器包含 `name` 参数时，THE Hatchet_Client SHALL 使用指定名称注册任务
4. WHEN 装饰器包含 `retries` 参数时，THE Hatchet_Client SHALL 配置任务的重试次数
5. WHEN 装饰器包含 `timeout` 参数时，THE Hatchet_Client SHALL 配置任务的超时时间
6. WHEN 被装饰的函数执行时，THE Hatchet_Client SHALL 通过 Hatchet 执行该任务并提供 Context 对象

### Requirement 3: 持久化定时（Durable Sleep）

**User Story:** 作为 Agent 开发者，我希望能够在任务中使用持久化定时，以便任务在等待期间进程重启后仍能继续执行。

#### Acceptance Criteria

1. THE Context SHALL 提供 `aio_sleep_for(seconds)` 方法用于持久化定时
2. WHEN 任务调用 `ctx.aio_sleep_for(seconds)` 时，THE Hatchet_Client SHALL 将定时状态持久化到 PostgreSQL
3. WHEN 定时期间 Worker 进程崩溃时，THE Hatchet_Server SHALL 在 Worker 重启后恢复定时
4. WHEN 定时到期时，THE Hatchet_Server SHALL 继续执行任务的后续代码
5. WHEN 定时参数为负数或零时，THE Hatchet_Client SHALL 抛出验证错误

### Requirement 4: 延迟执行和自我调度

**User Story:** 作为 Agent 开发者，我希望能够调度延迟执行的任务或让任务自我调度，以便实现 Agent 的自主调度能力。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 提供 `schedule_task(task_name, delay_seconds, **kwargs)` 方法
2. WHEN 调用 `schedule_task` 时，THE Hatchet_Client SHALL 创建一个延迟执行的 Hatchet 任务
3. WHEN `delay_seconds` 为正数时，THE Hatchet_Server SHALL 在指定延迟后执行任务
4. WHEN `kwargs` 包含任务参数时，THE Hatchet_Client SHALL 将参数传递给目标任务
5. WHEN 任务在自身内部调用 `schedule_task` 时，THE Hatchet_Client SHALL 支持自我调度（Agent 自主决定下次执行时间）
6. THE Hatchet_Client SHALL 返回调度任务的唯一标识符

### Requirement 5: Cron 触发器支持

**User Story:** 作为 OwlClaw 开发者，我希望能够使用 Cron 表达式定义周期性任务，以便替代传统的 cron 调度。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 支持在任务装饰器中指定 `cron` 参数
2. WHEN 任务装饰器包含 `cron` 参数时，THE Hatchet_Client SHALL 将任务注册为 Cron_Trigger
3. WHEN Cron 表达式有效时，THE Hatchet_Server SHALL 按照 Cron 表达式周期性触发任务
4. WHEN Cron 表达式无效时，THE Hatchet_Client SHALL 在注册时抛出验证错误
5. THE Hatchet_Client SHALL 支持标准 Cron 表达式格式（分 时 日 月 周）

### Requirement 6: 与 OwlClaw 配置系统集成

**User Story:** 作为 OwlClaw 用户，我希望能够通过 owlclaw.yaml 配置 Hatchet 连接参数，以便统一管理配置。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 从 `owlclaw.yaml` 的 `hatchet` 配置节读取连接参数
2. WHEN 配置包含 `server_url` 时，THE Hatchet_Client SHALL 使用指定的 Hatchet_Server 地址
3. WHEN 配置包含 `api_token` 时，THE Hatchet_Client SHALL 使用指定的认证令牌
4. WHEN 配置包含 `namespace` 时，THE Hatchet_Client SHALL 使用指定的命名空间隔离任务
5. WHEN 配置缺失必需参数时，THE Hatchet_Client SHALL 使用默认值或抛出配置错误
6. THE Hatchet_Client SHALL 使用 Pydantic 验证配置参数的类型和格式

### Requirement 7: 错误处理和重试策略

**User Story:** 作为 OwlClaw 开发者，我希望任务执行失败时能够自动重试，以便提高系统的容错能力。

#### Acceptance Criteria

1. WHEN 任务执行抛出异常时，THE Hatchet_Server SHALL 根据配置的重试策略自动重试
2. WHEN 重试次数达到上限时，THE Hatchet_Server SHALL 将任务标记为失败并停止重试
3. WHEN 任务失败时，THE Hatchet_Client SHALL 记录详细的错误信息和堆栈跟踪
4. THE Hatchet_Client SHALL 支持配置重试延迟策略（固定延迟、指数退避）
5. THE Hatchet_Client SHALL 支持配置哪些异常类型应该重试、哪些应该立即失败
6. WHEN 任务最终失败时，THE Hatchet_Client SHALL 触发失败回调（如果配置）

### Requirement 8: 开发模式支持（Hatchet Lite）

**User Story:** 作为 OwlClaw 开发者，我希望在开发环境中能够使用轻量级的 Hatchet 部署，以便快速启动和测试。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 支持连接到 Hatchet Lite（开发模式）
2. WHEN 配置指定 `mode: lite` 时，THE Hatchet_Client SHALL 使用简化的连接参数
3. WHEN 使用 Hatchet Lite 时，THE Hatchet_Client SHALL 支持所有核心功能（任务执行、定时、调度）
4. THE Hatchet_Client SHALL 在文档中说明 Hatchet Lite 与生产模式的差异
5. WHEN 从 Lite 模式切换到生产模式时，THE Hatchet_Client SHALL 只需要修改配置文件

### Requirement 9: 任务取消和状态查询

**User Story:** 作为 OwlClaw 开发者，我希望能够取消已调度的任务并查询任务状态，以便实现 Agent 的控制能力。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 提供 `cancel_task(task_id)` 方法用于取消已调度的任务
2. WHEN 任务尚未开始执行时，THE Hatchet_Server SHALL 取消任务并从队列中移除
3. WHEN 任务正在执行时，THE Hatchet_Server SHALL 发送取消信号并等待任务响应
4. THE Hatchet_Client SHALL 提供 `get_task_status(task_id)` 方法查询任务状态
5. WHEN 查询任务状态时，THE Hatchet_Client SHALL 返回任务的当前状态（pending、running、completed、failed、cancelled）
6. THE Hatchet_Client SHALL 提供 `list_scheduled_tasks()` 方法列出所有已调度的任务

### Requirement 10: database 级隔离（Hatchet 独立 database）

**User Story:** 作为 OwlClaw 部署者，我希望 Hatchet 使用 OwlClaw 拥有的同一 PostgreSQL 实例中的**独立 database**，以便简化部署且满足 Hatchet 对 DDL 权限的隔离要求。

#### Acceptance Criteria

1. THE 部署 SHALL 复用宿主已有的 PostgreSQL 实例，其中创建独立 database：**hatchet**（Hatchet 独占）、**owlclaw**（OwlClaw 业务：Ledger、Memory 等）。详见 `docs/DATABASE_ARCHITECTURE.md`。
2. WHEN Hatchet_Server 启动时，THE Hatchet_Server SHALL 连接至 **hatchet** database（DATABASE_URL 指向 `postgresql://hatchet:...@host:5432/hatchet`），不在 owlclaw database 中建表。
3. THE Hatchet_Client 与部署文档 SHALL 说明如何配置 database 级隔离（init 脚本创建 hatchet/owlclaw 库及对应用户）。
4. THE Hatchet_Server SHALL 支持 `SERVER_MSGQUEUE_KIND=postgres`，使用 PostgreSQL 作为消息队列，无需 RabbitMQ。
5. WHEN 使用独立 hatchet database 时，THE Hatchet_Server 的 migration 与表 SHALL 不影响 owlclaw database 中的 Ledger、Memory 等表。

### Requirement 11: 监控和可观测性

**User Story:** 作为 OwlClaw 运维者，我希望能够监控 Hatchet 任务的执行情况，以便及时发现和解决问题。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 记录所有任务执行的日志（开始、完成、失败）
2. WHEN 任务执行时，THE Hatchet_Client SHALL 记录任务名称、参数、执行时长
3. THE Hatchet_Client SHALL 支持集成 OpenTelemetry 进行分布式追踪
4. THE Hatchet_Server SHALL 提供内建的 Dashboard 用于可视化任务状态
5. THE Hatchet_Client SHALL 暴露 Prometheus 指标（任务执行次数、成功率、延迟）

### Requirement 12: 任务优先级和并发控制

**User Story:** 作为 OwlClaw 开发者，我希望能够控制任务的优先级和并发数，以便优化资源使用。

#### Acceptance Criteria

1. THE Hatchet_Client SHALL 支持在任务装饰器中指定 `priority` 参数
2. WHEN 多个任务在队列中等待时，THE Hatchet_Server SHALL 优先执行高优先级任务
3. THE Hatchet_Client SHALL 支持配置 Worker 的最大并发任务数
4. WHEN 并发任务数达到上限时，THE Hatchet_Server SHALL 将新任务放入队列等待
5. THE Hatchet_Client SHALL 支持为不同类型的任务配置不同的并发限制
