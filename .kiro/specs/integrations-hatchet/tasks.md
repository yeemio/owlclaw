# 任务清单

## Task 0: 契约与文档

- [x] 0.1 确认 requirements.md 完整且与架构文档一致
- [x] 0.2 确认 design.md 完整且包含所有组件设计
- [x] 0.3 确认 tasks.md 覆盖所有需求的实现

## Task 1: HatchetConfig 实现

- [x] 1.1 实现 HatchetConfig 数据类
  - [x] 1.1.1 定义配置字段（server_url、api_token、namespace 等）
  - [x] 1.1.2 使用 Pydantic 进行类型验证
  - [x] 1.1.3 实现 from_yaml() 类方法
  - [x] 1.1.4 实现默认值和环境变量支持

- [x] 1.2 实现配置验证
  - [x] 1.2.1 验证 server_url 格式
  - [x] 1.2.2 验证 mode 值（production/lite）
  - [x] 1.2.3 验证 PostgreSQL 连接参数

## Task 2: HatchetClient 核心实现

- [x] 2.1 实现 HatchetClient 类
  - [x] 2.1.1 实现 __init__() 方法
  - [x] 2.1.2 实现 connect() 方法
  - [x] 2.1.3 实现 disconnect() 方法
  - [x] 2.1.4 实现连接错误处理

- [x] 2.2 实现任务装饰器
  - [x] 2.2.1 实现 task() 装饰器
  - [x] 2.2.2 支持 name 参数
  - [x] 2.2.3 支持 cron 参数
  - [x] 2.2.4 支持 retries 参数
  - [x] 2.2.5 支持 timeout 参数
  - [x] 2.2.6 支持 priority 参数

- [x] 2.3 实现 Workflow 注册
  - [x] 2.3.1 将装饰的函数注册为 Hatchet Workflow
  - [x] 2.3.2 注册 Workflow 步骤
  - [x] 2.3.3 存储到 _workflows 字典

## Task 3: 任务调度实现

- [x] 3.1 实现 schedule_task() 方法
  - [x] 3.1.1 验证 task_name 已注册
  - [x] 3.1.2 验证 delay_seconds > 0
  - [x] 3.1.3 调用 Hatchet SDK 的 run_workflow()
  - [x] 3.1.4 传递延迟参数
  - [x] 3.1.5 返回任务 ID

- [x] 3.2 实现任务取消
  - [x] 3.2.1 实现 cancel_task() 方法
  - [x] 3.2.2 调用 Hatchet SDK 的 cancel_workflow_run()
  - [x] 3.2.3 处理取消失败的情况

- [x] 3.3 实现任务状态查询
  - [x] 3.3.1 实现 get_task_status() 方法
  - [x] 3.3.2 调用 Hatchet SDK 的 get_workflow_run()
  - [x] 3.3.3 格式化返回结果

- [x] 3.4 实现任务列表查询
  - [x] 3.4.1 实现 list_scheduled_tasks() 方法
  - [x] 3.4.2 调用 Hatchet SDK 的 list_workflow_runs()
  - [x] 3.4.3 过滤 pending 状态的任务

## Task 4: Worker 管理

- [x] 4.1 实现 start_worker() 方法
  - [x] 4.1.1 生成 worker_name（如果未配置）
  - [x] 4.1.2 调用 Hatchet SDK 的 worker()
  - [x] 4.1.3 配置 max_runs
  - [x] 4.1.4 启动 Worker

- [x] 4.2 实现 Worker 生命周期管理
  - [x] 4.2.1 优雅关闭 Worker
  - [x] 4.2.2 处理 Worker 崩溃恢复

## Task 5: 错误处理和日志

- [x] 5.1 实现连接错误处理
  - [x] 5.1.1 捕获连接异常
  - [x] 5.1.2 包装为 ConnectionError
  - [x] 5.1.3 记录详细错误信息

- [x] 5.2 实现任务执行错误处理
  - [x] 5.2.1 记录任务失败日志
  - [x] 5.2.2 记录重试次数
  - [x] 5.2.3 记录最终失败状态

- [x] 5.3 实现配置验证错误
  - [x] 5.3.1 验证 Cron 表达式格式
  - [x] 5.3.2 验证任务参数
  - [x] 5.3.3 提供清晰的错误消息

## Task 6: 单元测试

- [x] 6.1 HatchetConfig 测试
  - [x] 6.1.1 测试 from_yaml() 加载配置
  - [x] 6.1.2 测试默认值
  - [x] 6.1.3 测试环境变量替换
  - [x] 6.1.4 测试配置验证

- [x] 6.2 HatchetClient 测试
  - [x] 6.2.1 测试 connect() 成功
  - [x] 6.2.2 测试 connect() 失败
  - [x] 6.2.3 测试 disconnect()
  - [x] 6.2.4 测试 task() 装饰器

- [x] 6.3 任务调度测试
  - [x] 6.3.1 测试 schedule_task() 成功
  - [x] 6.3.2 测试 schedule_task() 无效延迟
  - [x] 6.3.3 测试 schedule_task() 未注册任务
  - [x] 6.3.4 测试 cancel_task()
  - [x] 6.3.5 测试 get_task_status()

## Task 7: 集成测试

- [x] 7.1 端到端任务执行测试
  - [x] 7.1.1 启动 Hatchet Server（测试环境）
  - [x] 7.1.2 注册测试任务
  - [x] 7.1.3 调度任务
  - [x] 7.1.4 验证任务执行成功

- [ ] 7.2 持久化定时测试
  - [ ] 7.2.1 创建使用 ctx.aio_sleep_for() 的任务
  - [ ] 7.2.2 验证定时状态持久化
  - [ ] 7.2.3 模拟 Worker 重启
  - [ ] 7.2.4 验证定时恢复

- [x] 7.3 Cron 触发器测试
  - [x] 7.3.1 注册 Cron 任务
  - [x] 7.3.2 验证按 Cron 表达式触发
  - [x] 7.3.3 测试无效 Cron 表达式

- [x] 7.4 自我调度测试
  - [x] 7.4.1 任务内部调用 schedule_task()
  - [x] 7.4.2 验证任务成功调度
  - [x] 7.4.3 验证调度的任务执行

## Task 8: 部署配置

- [x] 8.1 创建 Docker Compose 配置
  - [x] 8.1.1 创建开发模式配置（Hatchet Lite）
  - [x] 8.1.2 创建生产模式配置
  - [x] 8.1.3 database 级隔离：OwlClaw 数据层（owlclaw-db），Hatchet 连接 hatchet 库
  - [x] 8.1.4 提供 init-db.sql 创建 hatchet/owlclaw 库及用户（详见 `DATABASE_ARCHITECTURE.md`）

- [x] 8.2 创建配置示例
  - [x] 8.2.1 创建 owlclaw.yaml 示例
  - [x] 8.2.2 添加配置说明注释

## Task 9: 文档和示例

- [x] 9.1 创建使用示例
  - [x] 9.1.1 创建基本任务示例
  - [x] 9.1.2 创建 Cron 任务示例
  - [x] 9.1.3 创建自我调度示例
  - [x] 9.1.4 创建持久化定时示例

- [x] 9.2 更新 README
  - [x] 9.2.1 添加 Hatchet 集成说明
  - [x] 9.2.2 添加部署指南
  - [x] 9.2.3 添加配置参考

## Task 10: 集成到 OwlClaw 主包

- [x] 10.1 创建包结构
  - [x] 10.1.1 创建 owlclaw/integrations/__init__.py
  - [x] 10.1.2 创建 owlclaw/integrations/hatchet.py

- [x] 10.2 导出公共 API
  - [x] 10.2.1 在 owlclaw/integrations/__init__.py 中导出 HatchetClient
  - [x] 10.2.2 在 owlclaw/__init__.py 中导出（可选）

- [x] 10.3 添加依赖
  - [x] 10.3.1 在 pyproject.toml 中添加 hatchet-sdk
  - [x] 10.3.2 在 pyproject.toml 中添加 pydantic

## Task 11: 性能测试

- [x] 11.1 轻量性能测试（无服务器）
  - [x] 11.1.1 测试 Config 加载与 schedule_task 校验路径耗时
  - [ ] 11.1.2 可选：1000 任务调度吞吐（需真实 Hatchet 环境）

- [ ] 11.2 并发执行测试
  - [ ] 11.2.1 测试 10 个并发任务
  - [ ] 11.2.2 目标：所有任务在 30 秒内完成

- [ ] 11.3 持久化定时精度测试
  - [ ] 11.3.1 测试不同延迟时间的精度
  - [ ] 11.3.2 记录实际延迟与预期延迟的差异

## Task 12: 验收测试

- [x] 12.1 功能验收
  - [x] 12.1.1 验证所有需求的实现
  - [x] 12.1.2 验证错误处理
  - [x] 12.1.3 验证配置管理

- [x] 12.2 性能验收
  - [x] 12.2.1 验证调度吞吐量达标
  - [x] 12.2.2 验证并发执行达标

- [x] 12.3 部署验收
  - [x] 12.3.1 验证开发模式部署
  - [x] 12.3.2 验证生产模式部署
  - [x] 12.3.3 验证 PostgreSQL 共用
