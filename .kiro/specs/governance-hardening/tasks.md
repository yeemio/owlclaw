# governance-hardening — 任务清单

> **审计来源**: 2026-03-03-deep-audit-report-v4.md
> **优先级**: P1 (发布后需尽快修复)
> **最后更新**: 2026-03-03

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

---

## Phase 1：P1 治理问题（审计发现）

### Task 1：API Trigger 速率限制【P1 - Finding #8】
> API trigger 端点无速率限制，可被滥用导致成本失控
- [ ] 1.1 `triggers/api/server.py` 添加可配置的速率限制器
- [ ] 1.2 实现 per-tenant token bucket 限流
- [ ] 1.3 实现 per-endpoint 限流
- [ ] 1.4 单元测试：超限返回 429

### Task 2：VisibilityFilter fail_policy 默认值【P1 - Finding #9】
> 默认 fail_policy="open"，evaluator 失败时 capability 仍可见
- [x] 2.1 `visibility.py:158` 默认改为 `"close"`
- [x] 2.2 文档说明 `"open"` 仅用于 dev/test
- [x] 2.3 单元测试：evaluator 异常时 capability 被隐藏

### Task 3：Budget 约束竞态条件【P1 - Finding #10】
> check-then-act 模式无原子预约，并发请求可能突破预算
- [ ] 3.1 `budget.py` 实现原子预算预约机制
- [ ] 3.2 visibility check 时原子扣减，未执行时退款
- [ ] 3.3 单元测试：并发请求正确共享预算

---

## Phase 2：原有治理加固任务

### Task 4：Ledger 索引修复（REQ-G1）
- [ ] 4.1 新增 Alembic 迁移
- [ ] 4.2 验证索引

### Task 5：WebhookIdempotencyKeyModel UUID PK（REQ-G2）
- [ ] 5.1 修改模型
- [ ] 5.2 新增迁移
- [ ] 5.3 单元测试

### Task 6：Ledger fallback 路径（REQ-G3）
- [ ] 6.1 LedgerConfig 添加字段
- [ ] 6.2 ledger.py 使用配置路径
- [ ] 6.3 单元测试

### Task 7：MODEL_PRICING 扩展（REQ-G4）
- [ ] 7.1 添加新模型定价
- [ ] 7.2 单元测试

### Task 8：SkillQualityStore 索引（REQ-G5）
- [ ] 8.1 新增迁移
- [ ] 8.2 验证

### Task 9：env.py 导入 OwlHub 模型（REQ-G6）
- [ ] 9.1 添加 import
- [ ] 9.2 验证 autogenerate

### Task 10：Session factory 缓存（REQ-G7）
- [ ] 10.1 实现缓存
- [ ] 10.2 单元测试

### Task 11：DB 异常包装（REQ-G8）
- [ ] 11.1 捕获 + 包装异常
- [ ] 11.2 单元测试

### Task 12：DB SSL 配置（REQ-G9）
- [ ] 12.1 添加 ssl_mode 参数
- [ ] 12.2 文档

### Task 13：Cron 去重（REQ-G10）
- [ ] 13.1 添加并发保护
- [ ] 13.2 单元测试

---

## Task 14：回归测试
- [ ] 14.1 全量 pytest 通过
