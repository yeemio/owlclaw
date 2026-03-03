# runtime-robustness — 运行时健壮性修复

> **来源**: 2026-03-03 全方位审计
> **优先级**: P1（影响稳定性和可靠性）

---

## 背景

Agent Runtime 决策循环、app 生命周期、触发器系统存在多处健壮性问题：并发安全、资源泄漏、超时缺失、无限重试等。

---

## REQ-R1：_tool_call_timestamps 并发安全

- **现状**：`runtime.py:1272` 共享 deque 无锁，并发 trigger_event 可导致竞态
- **验收**：使用 asyncio.Lock 或 per-run 计数器

## REQ-R2：max_iterations 退出时保留最终响应

- **现状**：`runtime.py:854` 循环耗尽后 final_response 为空
- **验收**：最后一轮 tool results 被呈现给 LLM 或 final_response 包含有意义内容

## REQ-R3：Handler 超时机制

- **现状**：`registry.py:144` invoke_handler 无超时
- **验收**：handler 执行有可配置超时，超时返回错误

## REQ-R4：app.start() 幂等性

- **现状**：`app.py:708` 重复调用创建新 runtime 不清理旧的
- **验收**：第二次 start() 返回已有 runtime 或抛异常

## REQ-R5：app.start() 部分启动清理

- **现状**：`app.py:982` 启动中途失败不清理已启动组件
- **验收**：任何启动失败都触发 stop() 清理

## REQ-R6：mount_skills() 幂等性

- **现状**：`app.py:244` 第二次调用替换 registry 但不迁移 handler
- **验收**：第二次调用抛异常或正确迁移

## REQ-R7：db_change 重试限制

- **现状**：`db_change/manager.py:188` 无限重试
- **验收**：最大重试次数后移入 DLQ

## REQ-R8：InMemoryStore 线程安全

- **现状**：`store_inmemory.py:39` 无锁
- **验收**：添加 asyncio.Lock

## REQ-R9：InMemoryStore 大小限制

- **现状**：无上限，内存无限增长
- **验收**：可配置 max_entries

## REQ-R10：Hatchet 连接超时

- **现状**：`hatchet.py:184` connect() 无超时
- **验收**：连接有超时限制

## REQ-R11：skills_context_cache 跨租户隔离

- **现状**：`runtime.py:1553` cache key 不含 tenant_id
- **验收**：不同 tenant 不共享 cache

## REQ-R12：store_inmemory.py 解除 pgvector 硬依赖

- **现状**：`store_inmemory.py:14` 从 store_pgvector 导入 time_decay
- **验收**：time_decay 移到共享模块

## REQ-R13：WebSocket 断连清理

- **现状**：`ws.py:63` generator 未显式关闭
- **验收**：断连后资源正确释放

## REQ-R14：Langfuse atexit 重复注册

- **现状**：`langfuse.py:221` 每个 client 注册一个 atexit handler
- **验收**：仅注册一次

## REQ-R15：Redis idempotency 值序列化

- **现状**：`idempotency.py:39` 传 dict 给 Redis set()
- **验收**：json.dumps 序列化

## REQ-R16：Queue executor 连接复用

- **现状**：`queue_executor.py:61` 每次 execute 创建新 adapter
- **验收**：复用或池化 adapter

## REQ-R17：API trigger 无效 JSON 返回 400

- **现状**：`api/handler.py:21` 解析失败返回空 dict
- **验收**：返回 400 Bad Request

## REQ-R18：Prompt context window 检查

- **现状**：`runtime.py:1185` 系统提示无总 token 限制
- **验收**：总 prompt 不超过模型 context window
