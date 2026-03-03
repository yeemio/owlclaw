# runtime-robustness — 任务清单

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

## Task 1：_tool_call_timestamps 并发安全（REQ-R1）
- [x] 1.1 改为 per-run 计数器或加锁
- [x] 1.2 单元测试

## Task 2：max_iterations 最终响应（REQ-R2）
- [x] 2.1 循环耗尽后追加一轮 LLM 调用
- [x] 2.2 单元测试

## Task 3：Handler 超时（REQ-R3）
- [ ] 3.1 registry.invoke_handler 添加 asyncio.wait_for
- [ ] 3.2 单元测试

## Task 4：start() 幂等（REQ-R4）
- [ ] 4.1 添加 _runtime 检查
- [ ] 4.2 单元测试

## Task 5：部分启动清理（REQ-R5）
- [ ] 5.1 start() try/except + stop()
- [ ] 5.2 单元测试

## Task 6：mount_skills() 幂等（REQ-R6）
- [ ] 6.1 添加重复调用检查
- [ ] 6.2 单元测试

## Task 7：db_change 重试限制（REQ-R7）
- [ ] 7.1 添加 max_retries + DLQ
- [ ] 7.2 单元测试

## Task 8：InMemoryStore 线程安全（REQ-R8）
- [ ] 8.1 添加 asyncio.Lock
- [ ] 8.2 单元测试

## Task 9：InMemoryStore 大小限制（REQ-R9）
- [ ] 9.1 添加 max_entries + LRU
- [ ] 9.2 单元测试

## Task 10：Hatchet 连接超时（REQ-R10）
- [ ] 10.1 connect() 添加超时
- [ ] 10.2 单元测试

## Task 11：skills_context_cache 隔离（REQ-R11）
- [x] 11.1 cache key 添加 tenant_id
- [x] 11.2 单元测试

## Task 12：time_decay 提取（REQ-R12）
- [ ] 12.1 创建 decay.py 移入函数
- [ ] 12.2 更新 import
- [ ] 12.3 单元测试

## Task 13：WebSocket 断连清理（REQ-R13）
- [ ] 13.1 显式关闭 generator
- [ ] 13.2 单元测试

## Task 14：Langfuse atexit 去重（REQ-R14）
- [ ] 14.1 添加模块级标志
- [ ] 14.2 单元测试

## Task 15：Redis idempotency 序列化（REQ-R15）
- [ ] 15.1 json.dumps 序列化
- [ ] 15.2 单元测试

## Task 16：Queue executor 连接复用（REQ-R16）
- [ ] 16.1 adapter 缓存/池化
- [ ] 16.2 单元测试

## Task 17：API trigger 400（REQ-R17）
- [ ] 17.1 返回 400 Bad Request
- [ ] 17.2 单元测试

## Task 18：Prompt context window 检查（REQ-R18）
- [ ] 18.1 总 token 估算 + 截断
- [ ] 18.2 单元测试

## Task 19：回归测试
- [ ] 19.1 全量 pytest 通过
