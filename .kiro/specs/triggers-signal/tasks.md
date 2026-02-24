# Signal 触发器实现任务

## 文档联动

- requirements: `.kiro/specs/triggers-signal/requirements.md`
- design: `.kiro/specs/triggers-signal/design.md`
- tasks: `.kiro/specs/triggers-signal/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## 任务列表

### Phase 0：协议契约先行（Protocol-first，决策 4.11）

- [x] **Task 0**: 定义 Signal 协议契约
  - [x] 0.1 提交 Signal 请求/响应 JSON Schema（pause/resume/trigger/instruct 四种操作的 schema 与错误码表）
  - [x] 0.2 确认三条入口（CLI/HTTP API/MCP）共用同一协议 schema，不各自定义独立格式
  - [x] 0.3 协议层不泄漏 Python 特有语义（无 Callable/装饰器元数据）
  - _说明：Task 1 的 Python 实现必须从本契约派生，禁止跳过契约直接做 Python API_

### Phase 1：核心 Signal 框架

- [x] **Task 1**: 创建 `owlclaw/triggers/signal/` 模块结构
  - 创建 `__init__.py`, `models.py`, `router.py`, `handlers.py`, `state.py`, `config.py`
  - 定义 `Signal`, `SignalType`, `SignalSource`, `SignalResult` 数据模型
  - 定义 `PendingInstruction` 数据模型

- [ ] **Task 2**: 实现 `AgentStateManager`
  - 创建 Alembic migration：agents 表增加 `paused` 列 + `pending_instructions` 表
  - 实现 `get()` / `set_paused()` Agent 状态读写
  - 实现 `add_instruction()` / `consume_instructions()` 指令管理
  - 实现 `cleanup_expired_instructions()` 过期清理
  - 确保 `tenant_id` 隔离

- [x] **Task 3**: 实现 `SignalRouter` 统一分发
  - Signal 接收 + 权限验证
  - 按 SignalType 分发到对应 Handler
  - Ledger 记录所有 Signal 操作
  - 错误处理（Agent 不存在、权限不足等）

- [ ] **Task 4**: 实现 `PauseHandler` + `ResumeHandler`
  - PauseHandler: 设置 paused=True + 暂停 Hatchet cron
  - ResumeHandler: 设置 paused=False + 恢复 Hatchet cron
  - 幂等处理（已暂停再暂停 → already_paused）
  - 状态持久化（进程重启后保持）

- [ ] **Task 5**: 实现 `TriggerHandler`
  - 强制触发 Agent Run（不受 paused 影响）
  - 支持 focus 和 message 参数
  - 治理检查（预算/限流）
  - 返回 run_id

- [ ] **Task 6**: 实现 `InstructHandler`
  - 写入 pending_instructions 表
  - TTL 支持（默认 1 小时）
  - 最大待处理指令数限制（防止堆积）

### Phase 2：多入口集成

- [ ] **Task 7**: 实现 CLI 命令
  - `owlclaw agent pause [--agent-id <id>]`
  - `owlclaw agent resume [--agent-id <id>]`
  - `owlclaw agent trigger --focus <focus> --message <msg>`
  - `owlclaw agent instruct --message <msg> [--ttl <seconds>]`
  - `owlclaw agent status [--agent-id <id>]`
  - 所有命令构造 Signal 对象 → SignalRouter.dispatch()

- [ ] **Task 8**: 实现 HTTP API 入口
  - POST `/admin/signal` 通用 Signal 端点
  - 认证中间件（Bearer Token）
  - 请求体验证（Pydantic）
  - 与 API 触发器共享 Starlette 服务

- [ ] **Task 9**: 实现 MCP Server 集成
  - `owlclaw_pause` MCP tool → Signal(type=PAUSE, source=MCP)
  - `owlclaw_resume` MCP tool → Signal(type=RESUME, source=MCP)
  - `owlclaw_trigger` MCP tool → Signal(type=TRIGGER, source=MCP)
  - `owlclaw_instruct` MCP tool → Signal(type=INSTRUCT, source=MCP)

### Phase 3：Agent Runtime 集成

- [ ] **Task 10**: Agent Runtime paused 状态检查
  - Cron/Heartbeat 触发前检查 paused 状态
  - paused 时跳过 Run 并记录 status=SKIPPED
  - Signal.TRIGGER 不受 paused 影响

- [ ] **Task 11**: Instruction 注入到 Agent Run
  - Run 启动时 consume_instructions()
  - 注入到 STM 的固定区
  - 消费后标记 consumed=True
  - Ledger 记录指令消费事件

### Phase 4：测试

- [ ] **Task 12**: 单元测试
  - Signal 数据模型验证
  - 各 Handler 逻辑（pause/resume/trigger/instruct）
  - AgentStateManager CRUD
  - Instruction TTL 过期逻辑
  - 目标覆盖率：> 90%

- [ ] **Task 13**: 集成测试
  - CLI → SignalRouter → State 变更 全流程
  - HTTP API → SignalRouter → State 变更 全流程
  - pause → cron 不触发 → resume → cron 恢复
  - instruct → Agent Run → STM 包含指令

- [ ] **Task 14**: 文档
  - Signal 系统使用指南
  - CLI 命令参考
  - MCP 工具集成说明
  - 人工介入最佳实践（何时暂停、何时注入指令）
