# 数据库变更触发器实现任务

## 文档联动

- requirements: `.kiro/specs/triggers-db-change/requirements.md`
- design: `.kiro/specs/triggers-db-change/design.md`
- tasks: `.kiro/specs/triggers-db-change/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 任务列表

### Phase 1：核心监听与聚合

- [x] **Task 1**: 创建 `owlclaw/triggers/db_change/` 模块结构
  - 创建 `__init__.py`, `adapter.py`, `aggregator.py`, `manager.py`, `config.py`
  - 定义 `DBChangeEvent` dataclass
  - 定义 `DBChangeAdapter` 抽象基类
  - 定义 `DBChangeTriggerConfig` Pydantic 模型

- [x] **Task 2**: 实现 `PostgresNotifyAdapter`
  - asyncpg LISTEN 多通道并发监听
  - NOTIFY payload JSON 解析 + 错误处理
  - 连接健康检查 + 自动重连（可配置间隔）
  - 优雅停止（取消所有 listener，关闭连接）

- [x] **Task 3**: 实现 `EventAggregator`
  - debounce 策略：窗口期内只 flush 最后一批
  - batch 策略：累积到 batch_size 后 flush
  - 混合模式：先 batch，batch 满前到达 debounce 超时也 flush
  - 无聚合模式：直通 flush
  - 线程安全（asyncio Lock）

- [x] **Task 4**: 实现 `DBChangeTriggerManager`
  - register() 注册触发器 → 创建 aggregator
  - 与 GovernanceService 集成（cooldown/rate limit/budget）
  - 与 AgentRunner 集成（dispatch Hatchet task）
  - 与 Ledger 集成（记录触发/阻断事件）

- [x] **Task 5**: 实现装饰器 + 函数调用 API
  - `@app.db_change()` 装饰器（fallback handler 绑定）
  - `app.trigger(db_change(...))` 函数调用风格
  - 触发器注册到 DBChangeTriggerManager

- [x] **Task 6**: 创建 PostgreSQL NOTIFY 触发器模板
  - SQL 模板文件 `templates/notify_trigger.sql`
  - CLI `owlclaw trigger template db-change` 生成到项目目录
  - 模板支持 INSERT/UPDATE/DELETE 事件

### Phase 2：测试与降级

- [x] **Task 7**: 单元测试
  - EventAggregator：debounce/batch/混合/直通 四种模式
  - DBChangeEvent 解析：正常/空 payload/非 JSON
  - DBChangeTriggerManager：register/trigger/governance block
  - 目标覆盖率：> 90%

- [x] **Task 8**: 集成测试
  - 使用 testcontainers 启动 PostgreSQL
  - 创建测试表 + NOTIFY trigger function
  - 验证 INSERT → NOTIFY → Adapter → Aggregator → Agent trigger 全流程
  - 验证连接断开 → 自动重连 → 不丢后续事件

- [x] **Task 9**: 降级与边界处理
  - 大 payload 处理（PostgreSQL NOTIFY 限制 8000 bytes）
  - 超长未消费事件的内存保护
  - Hatchet 不可用时的本地队列缓冲

### Phase 3：CDC 预留

- [x] **Task 10**: 定义 CDC 适配器接口
  - `DebeziumAdapter(DBChangeAdapter)` 接口定义（不实现）
  - CDC 配置模型
  - 文档：如何扩展 CDC 适配器

- [x] **Task 11**: 文档
  - PostgreSQL NOTIFY 触发器设置指南
  - 事件聚合参数调优指南
  - CDC 扩展路线图
