# runtime-robustness — 设计文档

> **来源**: `requirements.md` REQ-R1 ~ REQ-R18

---

## D-R1：_tool_call_timestamps 并发安全

方案 A（推荐）：改为 per-run 计数器，不共享。
方案 B：添加 `asyncio.Lock`。

## D-R2：max_iterations 最终响应

在循环结束后，如果最后消息是 tool result，追加一轮 LLM 调用获取总结。

## D-R3：Handler 超时

`registry.invoke_handler()` 包裹 `asyncio.wait_for(handler(...), timeout=config.handler_timeout)`。默认 30s。

## D-R4：start() 幂等

`start()` 开头检查 `self._runtime is not None`，已启动则返回。

## D-R5：部分启动清理

`start()` 内部 try/except，失败时调用 `stop()`。

## D-R6：mount_skills() 幂等

第二次调用时 raise `RuntimeError("mount_skills() already called")`。

## D-R7：db_change 重试限制

添加 `max_retries` 配置（默认 5），超过后记录到 DLQ 日志。

## D-R8：InMemoryStore 加锁

所有 save/search/delete 操作用 `asyncio.Lock`。

## D-R9：InMemoryStore 大小限制

添加 `max_entries` 参数，超过时 LRU 淘汰。

## D-R10：Hatchet 连接超时

`connect()` 包裹 `asyncio.wait_for(..., timeout=30)`。

## D-R11：skills_context_cache 隔离

cache key 添加 `context.tenant_id`。

## D-R12：time_decay 提取

创建 `owlclaw/agent/memory/decay.py`，移入 `time_decay` 函数。

## D-R13：WebSocket 清理

`_stream_messages` 使用 `async with` 或显式 `aclose()`。

## D-R14：Langfuse atexit 去重

使用模块级 `_atexit_registered` 标志。

## D-R15：Redis 值序列化

`set()` 前 `json.dumps(value)`。

## D-R16：Queue executor 连接复用

使用 `_adapter_cache: dict[str, QueueAdapter]`。

## D-R17：API trigger 400

JSON 解析失败返回 `JSONResponse(status_code=400, content={"error": "Invalid JSON"})`。

## D-R18：Context window 检查

在 `_build_messages()` 后估算总 token，超过模型限制时截断 skills context。

---

## 影响文件

| 文件 | 修改 |
|------|------|
| `owlclaw/agent/runtime/runtime.py` | R1, R2, R11, R18 |
| `owlclaw/capabilities/registry.py` | R3 |
| `owlclaw/app.py` | R4, R5, R6 |
| `owlclaw/triggers/db_change/manager.py` | R7 |
| `owlclaw/agent/memory/store_inmemory.py` | R8, R9, R12 |
| `owlclaw/agent/memory/decay.py` | R12（新文件） |
| `owlclaw/integrations/hatchet.py` | R10 |
| `owlclaw/web/api/ws.py` | R13 |
| `owlclaw/integrations/langfuse.py` | R14 |
| `owlclaw/triggers/queue/idempotency.py` | R15 |
| `owlclaw/capabilities/bindings/queue_executor.py` | R16 |
| `owlclaw/triggers/api/handler.py` | R17 |
