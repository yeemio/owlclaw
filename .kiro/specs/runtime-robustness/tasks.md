# runtime-robustness — 任务清单

> **审计来源**: 2026-03-03-deep-audit-report-v4.md
> **优先级**: P0 (阻塞发布)
> **最后更新**: 2026-03-03

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

---

## Phase 1：P0 健壮性问题（阻塞发布）

### Task 1：工具参数 Schema 校验【P0 - Finding #3】
> 见 security-hardening Task 2，此处为依赖声明
- [ ] 1.0 依赖 security-hardening Task 2 完成

### Task 2：_tool_call_timestamps 并发安全（REQ-R1）【P1 - Finding #16】
> deque 无锁更新，并发 run 可破坏或绕过速率限制
- [ ] 2.1 改为 per-run 计数器或添加 `asyncio.Lock`
- [ ] 2.2 单元测试：并发 run 不互相干扰

### Task 3：skills_context_cache 隔离（REQ-R11）【P1 - Finding #17】
> cache key 缺失 tenant_id，多租户数据可能混淆
- [ ] 3.1 `runtime.py:1559` cache key 添加 `tenant_id`
- [ ] 3.2 单元测试：不同 tenant 的 cache 不互相污染

---

## Phase 2：P1 健壮性加固

### Task 4：max_iterations 最终响应（REQ-R2）
- [ ] 4.1 循环耗尽后追加一轮 LLM 调用
- [ ] 4.2 单元测试

### Task 5：Handler 超时（REQ-R3）
- [ ] 5.1 registry.invoke_handler 添加 asyncio.wait_for
- [ ] 5.2 单元测试

### Task 6：start() 幂等（REQ-R4）
- [ ] 6.1 添加 _runtime 检查
- [ ] 6.2 单元测试

### Task 7：部分启动清理（REQ-R5）
- [ ] 7.1 start() try/except + stop()
- [ ] 7.2 单元测试

### Task 8：mount_skills() 幂等（REQ-R6）
- [ ] 8.1 添加重复调用检查
- [ ] 8.2 单元测试

### Task 9：db_change 重试限制（REQ-R7）
- [ ] 9.1 添加 max_retries + DLQ
- [ ] 9.2 单元测试

### Task 10：InMemoryStore 线程安全（REQ-R8）
- [ ] 10.1 添加 asyncio.Lock
- [ ] 10.2 单元测试

### Task 11：InMemoryStore 大小限制（REQ-R9）
- [ ] 11.1 添加 max_entries + LRU
- [ ] 11.2 单元测试

### Task 12：Hatchet 连接超时（REQ-R10）
- [ ] 12.1 connect() 添加超时
- [ ] 12.2 单元测试

### Task 13：time_decay 提取（REQ-R12）
- [ ] 13.1 创建 decay.py 移入函数
- [ ] 13.2 更新 import
- [ ] 13.3 单元测试

### Task 14：WebSocket 断连清理（REQ-R13）
- [ ] 14.1 显式关闭 generator
- [ ] 14.2 单元测试

### Task 15：Langfuse atexit 去重（REQ-R14）
- [ ] 15.1 添加模块级标志
- [ ] 15.2 单元测试

### Task 16：Redis idempotency 序列化（REQ-R15）
- [ ] 16.1 json.dumps 序列化
- [ ] 16.2 单元测试

### Task 17：Queue executor 连接复用（REQ-R16）
- [ ] 17.1 adapter 缓存/池化
- [ ] 17.2 单元测试

### Task 18：API trigger 400（REQ-R17）
- [ ] 18.1 返回 400 Bad Request
- [ ] 18.2 单元测试

### Task 19：Prompt context window 检查（REQ-R18）
- [ ] 19.1 总 token 估算 + 截断
- [ ] 19.2 单元测试

---

## Task 20：回归测试
- [ ] 20.1 全量 pytest 通过
