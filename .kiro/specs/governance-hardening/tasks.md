# governance-hardening — 任务清单

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

## Task 1：Ledger 索引修复（REQ-G1）
- [x] 1.1 新增 Alembic 迁移
- [x] 1.2 验证索引

## Task 2：WebhookIdempotencyKeyModel UUID PK（REQ-G2）
- [x] 2.1 修改模型
- [x] 2.2 新增迁移
- [x] 2.3 单元测试

## Task 3：Ledger fallback 路径（REQ-G3）
- [x] 3.1 LedgerConfig 添加字段
- [x] 3.2 ledger.py 使用配置路径
- [x] 3.3 单元测试

## Task 4：MODEL_PRICING 扩展（REQ-G4）
- [x] 4.1 添加新模型定价
- [x] 4.2 单元测试

## Task 5：SkillQualityStore 索引（REQ-G5）
- [x] 5.1 新增迁移
- [x] 5.2 验证

## Task 6：env.py 导入 OwlHub 模型（REQ-G6）
- [x] 6.1 添加 import
- [x] 6.2 验证 autogenerate

## Task 7：Session factory 缓存（REQ-G7）
- [ ] 7.1 实现缓存
- [ ] 7.2 单元测试

## Task 8：DB 异常包装（REQ-G8）
- [ ] 8.1 捕获 + 包装异常
- [ ] 8.2 单元测试

## Task 9：DB SSL 配置（REQ-G9）
- [ ] 9.1 添加 ssl_mode 参数
- [ ] 9.2 文档

## Task 10：Cron 去重（REQ-G10）
- [ ] 10.1 添加并发保护
- [ ] 10.2 单元测试

## Task 11：回归测试
- [ ] 11.1 全量 pytest 通过
