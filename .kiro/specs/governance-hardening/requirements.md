# governance-hardening — 治理层加固

> **来源**: 2026-03-03 全方位审计
> **优先级**: P1（治理层缺陷影响 Agent 可控性）

---

## 背景

治理层（Governance）的多个组件存在实效性问题：数据库索引不合规、Ledger 回退路径风险、模型定价不完整等。

---

## REQ-G1：Ledger 索引添加 tenant_id 前缀

- **现状**：`migration 002` 的索引缺少 tenant_id 前缀
- **验收**：所有 Ledger 索引为 `(tenant_id, ...)` 复合索引

## REQ-G2：WebhookIdempotencyKeyModel 使用 UUID 主键

- **现状**：`webhook/persistence/models.py:74` 使用 `key: str` 作为主键
- **验收**：添加 `id: UUID` 主键，key 改为 unique index

## REQ-G3：Ledger fallback 路径可配置

- **现状**：`governance/ledger.py:361` 硬编码 `"ledger_fallback.log"`
- **验收**：路径从配置读取

## REQ-G4：MODEL_PRICING 扩展

- **现状**：`langfuse.py:116` 仅覆盖少量模型
- **验收**：添加 DeepSeek、Claude 等常用模型定价

## REQ-G5：SkillQualityStore 索引合规

- **现状**：`quality_store.py:38` 索引缺少 tenant_id
- **验收**：复合索引

## REQ-G6：Alembic env.py 导入 OwlHub 模型

- **现状**：`migrations/env.py` 未导入 OwlHub 模型
- **验收**：autogenerate 包含 OwlHub 表

## REQ-G7：Session factory 缓存

- **现状**：`db/session.py:48` 每次调用创建新 factory
- **验收**：按 engine 缓存

## REQ-G8：DB 连接失败包装为自定义异常

- **现状**：`db/engine.py` 原始 asyncpg 异常泄漏
- **验收**：包装为 `DatabaseConnectionError`

## REQ-G9：DB SSL/TLS 配置

- **现状**：`db/engine.py` 无 SSL 配置
- **验收**：支持 `connect_args` 或 URL 参数

## REQ-G10：Cron 任务去重

- **现状**：无重叠运行保护
- **验收**：同一 cron 任务不并行执行

## REQ-G11：API Trigger 速率限制

- **现状**：`triggers/api/server.py` 无内置速率限制
- **验收**：支持可配置的 per-tenant 与 per-endpoint token bucket，超限返回 429

## REQ-G12：VisibilityFilter 默认 fail_policy=close

- **现状**：默认 `fail_policy="open"`，评估器异常时 capability 继续可见
- **验收**：默认改为 `close`；文档明确 `open` 仅用于 dev/test

## REQ-G13：Budget 原子预约与退款

- **现状**：budget 检查为 check-then-act，并发请求可能共同通过
- **验收**：预算检查与预约原子化；未执行请求可退款或自动过期释放
