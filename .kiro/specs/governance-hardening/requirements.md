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
