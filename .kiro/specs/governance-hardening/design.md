# governance-hardening — 设计文档

> **来源**: `requirements.md` REQ-G1 ~ REQ-G10

---

## D-G1：Ledger 索引修复

新增 Alembic 迁移：drop 旧单列索引，create 复合索引 `(tenant_id, agent_id)` 等。

## D-G2：WebhookIdempotencyKeyModel UUID PK

添加 `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`，`key` 改为 `unique=True`。

## D-G3：Ledger fallback 路径

`LedgerConfig` 添加 `fallback_log_path: str = "ledger_fallback.log"`。

## D-G4：MODEL_PRICING 扩展

添加 deepseek-chat、deepseek-reasoner、claude-3.5-sonnet、claude-3-opus 等。

## D-G5：SkillQualityStore 索引

新增迁移修复索引。

## D-G6：env.py 导入

添加 `from owlclaw.owlhub.models import *`。

## D-G7：Session factory 缓存

模块级 `_session_factory_cache: dict[int, async_sessionmaker]`，key 为 engine id。

## D-G8：DB 异常包装

`get_engine()` 和 `get_session()` 捕获 asyncpg 异常，包装为 `DatabaseConnectionError`。

## D-G9：DB SSL

`get_engine()` 支持 `ssl_mode` 参数，映射到 `connect_args`。

## D-G10：Cron 去重

使用 Hatchet 的 `concurrency` 配置或本地 `asyncio.Lock`。

## D-G11：API Trigger 速率限制

在 `APITriggerServer` 增加可配置的 token bucket 限流器：
- `tenant_rate_limit_per_minute`
- `endpoint_rate_limit_per_minute`
超限返回 HTTP 429，并记录 ledger blocked 事件。

## D-G12：VisibilityFilter 默认 fail-close

`VisibilityFilter.__init__` 默认 `fail_policy="close"`。
`app._ensure_governance()` 与 `config.models.GovernanceConfig` 默认值同步为 `close`，
并在字段说明中标注 `open` 仅用于 dev/test 调试。

## D-G13：Budget 原子预约与退款

`BudgetConstraint` 内维护带锁的预算预约表（按 tenant_id + agent_id 分桶）：
- evaluate 时原子计算 `remaining = limit - used - reserved`
- 对高成本 capability 进行预约，避免并发穿透
- 提供退款接口并支持 TTL 过期回收

---

## 影响文件

| 文件 | 修改 |
|------|------|
| `migrations/versions/` | G1, G2, G5 新迁移 |
| `owlclaw/triggers/webhook/persistence/models.py` | G2 |
| `owlclaw/governance/ledger.py` | G3 |
| `owlclaw/integrations/langfuse.py` | G4 |
| `owlclaw/governance/quality_store.py` | G5 |
| `migrations/env.py` | G6 |
| `owlclaw/db/session.py` | G7 |
| `owlclaw/db/engine.py` | G8, G9 |
| `owlclaw/triggers/cron.py` | G10 |
| `owlclaw/triggers/api/server.py` | G11 |
| `owlclaw/governance/visibility.py` | G12 |
| `owlclaw/config/models.py` + `owlclaw/app.py` | G12 |
| `owlclaw/governance/constraints/budget.py` | G13 |
