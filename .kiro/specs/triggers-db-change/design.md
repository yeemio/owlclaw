# 数据库变更触发器设计文档

## 文档联动

- requirements: `.kiro/specs/triggers-db-change/requirements.md`
- design: `.kiro/specs/triggers-db-change/design.md`
- tasks: `.kiro/specs/triggers-db-change/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

数据库变更触发器通过 PostgreSQL NOTIFY/LISTEN 机制监听数据变更事件，经过事件聚合（debounce/batch）后触发 Agent Run。采用适配器模式预留 CDC 扩展接口。

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. NOTIFY/LISTEN 仅作为触发输入通道，不替代业务审计存储；审计落库仍需满足 `tenant_id` 与时间类型规范。
2. CDC 扩展作为适配器层能力，禁止在核心触发器层绑定特定供应商实现。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                    PostgreSQL                              │
│                                                            │
│  ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  Application │    │  NOTIFY trigger function          │ │
│  │  Tables      │───→│  PERFORM pg_notify('channel',    │ │
│  │              │    │    json_build_object(...))         │ │
│  └─────────────┘    └──────────────┬───────────────────┘ │
└──────────────────────────────────────┼────────────────────┘
                                       │ NOTIFY
                                       ▼
┌──────────────────────────────────────────────────────────┐
│                 OwlClaw DB Change Trigger                  │
│                                                            │
│  ┌─────────────────┐                                     │
│  │  ListenerManager │   asyncpg LISTEN                    │
│  │  (per channel)   │   自动重连                           │
│  └────────┬────────┘                                     │
│           │ raw events                                     │
│           ▼                                                │
│  ┌─────────────────┐                                     │
│  │ EventAggregator  │   debounce / batch                  │
│  │ (per channel)    │                                     │
│  └────────┬────────┘                                     │
│           │ aggregated events                              │
│           ▼                                                │
│  ┌─────────────────┐                                     │
│  │ GovernanceCheck  │   cooldown / rate limit / budget     │
│  └────────┬────────┘                                     │
│           │ approved events                                │
│           ▼                                                │
│  ┌─────────────────┐                                     │
│  │ AgentRunTrigger  │   → Hatchet task dispatch            │
│  └─────────────────┘                                     │
└──────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. DBChangeAdapter（抽象基类）

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class DBChangeEvent:
    channel: str
    payload: dict
    timestamp: datetime
    source: str  # "notify" | "cdc"

class DBChangeAdapter(ABC):
    @abstractmethod
    async def start(self, channels: list[str]) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def on_event(self, callback: Callable[[DBChangeEvent], Awaitable[None]]) -> None: ...
```

### 2. PostgresNotifyAdapter（NOTIFY/LISTEN 实现）

```python
class PostgresNotifyAdapter(DBChangeAdapter):
    def __init__(self, dsn: str, reconnect_interval: float = 30.0):
        self._conn: asyncpg.Connection | None = None
        self._dsn = dsn
        self._reconnect_interval = reconnect_interval
        self._callbacks: list[Callable] = []
        self._running = False

    async def start(self, channels: list[str]) -> None:
        self._running = True
        self._conn = await asyncpg.connect(self._dsn)
        for ch in channels:
            await self._conn.add_listener(ch, self._on_notify)
        asyncio.create_task(self._health_check_loop())

    async def _on_notify(self, conn, pid, channel, payload):
        event = DBChangeEvent(
            channel=channel,
            payload=json.loads(payload) if payload else {},
            timestamp=datetime.utcnow(),
            source="notify",
        )
        for cb in self._callbacks:
            await cb(event)

    async def _health_check_loop(self):
        """连接健康检查 + 自动重连"""
        while self._running:
            try:
                await self._conn.execute("SELECT 1")
            except Exception:
                await self._reconnect()
            await asyncio.sleep(self._reconnect_interval)
```

### 3. EventAggregator（事件聚合器）

```python
class EventAggregator:
    """支持 debounce 和 batch 两种聚合策略"""

    def __init__(
        self,
        debounce_seconds: float | None = None,
        batch_size: int | None = None,
        on_flush: Callable[[list[DBChangeEvent]], Awaitable[None]] = None,
    ):
        self._buffer: list[DBChangeEvent] = []
        self._debounce_timer: asyncio.TimerHandle | None = None
        self._debounce_seconds = debounce_seconds
        self._batch_size = batch_size
        self._on_flush = on_flush

    async def push(self, event: DBChangeEvent):
        self._buffer.append(event)

        if self._batch_size and len(self._buffer) >= self._batch_size:
            await self._flush()
            return

        if self._debounce_seconds:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            loop = asyncio.get_event_loop()
            self._debounce_timer = loop.call_later(
                self._debounce_seconds, lambda: asyncio.ensure_future(self._flush())
            )
        elif not self._batch_size:
            # 无聚合，直接触发
            await self._flush()

    async def _flush(self):
        if not self._buffer:
            return
        events = self._buffer.copy()
        self._buffer.clear()
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None
        await self._on_flush(events)
```

### 4. DBChangeTriggerManager

```python
class DBChangeTriggerManager:
    """管理所有 db_change 触发器的注册和生命周期"""

    def __init__(
        self,
        adapter: DBChangeAdapter,
        governance: GovernanceService,
        agent_runner: AgentRunner,
        ledger: Ledger,
    ): ...

    def register(self, config: DBChangeTriggerConfig) -> None:
        """注册一个 db_change 触发器"""
        aggregator = EventAggregator(
            debounce_seconds=config.debounce_seconds,
            batch_size=config.batch_size,
            on_flush=lambda events: self._on_aggregated(config, events),
        )
        self._triggers[config.channel] = (config, aggregator)

    async def _on_aggregated(self, config: DBChangeTriggerConfig, events: list[DBChangeEvent]):
        if not await self.governance.check(config.event_name):
            self.ledger.record(event_name=config.event_name, status="GOVERNANCE_BLOCKED")
            return

        await self.agent_runner.trigger(
            event_name=config.event_name,
            trigger_type="db_change",
            payload={
                "channel": config.channel,
                "events": [e.payload for e in events],
                "event_count": len(events),
            },
            focus=config.focus,
        )
        self.ledger.record(event_name=config.event_name, status="TRIGGERED", event_count=len(events))
```

### 5. API 集成（装饰器 + 函数调用双模式）

```python
# 装饰器风格
@app.db_change(
    channel="position_changes",
    event_name="position_changed",
    debounce_seconds=5,
    focus="position_monitor",
)
async def on_position_change(events: list[dict]):
    """Fallback: 固定处理"""
    for e in events:
        await legacy_position_handler(e)

# 函数调用风格
from owlclaw.triggers import db_change
app.trigger(db_change(
    channel="order_updates",
    event_name="order_changed",
    batch_size=10,
))
```

## PostgreSQL 触发器模板

业务开发者需要在应用数据库中创建 NOTIFY 触发器：

```sql
-- owlclaw 提供的模板，用户按需修改
CREATE OR REPLACE FUNCTION notify_position_changes()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('position_changes', json_build_object(
        'operation', TG_OP,
        'table', TG_TABLE_NAME,
        'id', COALESCE(NEW.id, OLD.id),
        'data', row_to_json(COALESCE(NEW, OLD))
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER position_changes_trigger
    AFTER INSERT OR UPDATE OR DELETE ON positions
    FOR EACH ROW EXECUTE FUNCTION notify_position_changes();
```

## 降级策略

| 场景 | 行为 |
|------|------|
| LISTEN 连接断开 | 自动重连（30s 间隔），期间事件丢失 |
| NOTIFY payload 解析失败 | 记录 WARNING，跳过该事件 |
| Hatchet 不可用 | 事件写入本地队列，恢复后重放 |

## 配置模型

```yaml
triggers:
  db_change:
    adapter: notify          # notify | cdc (未来)
    reconnect_interval: 30
    max_channels: 50
    default_debounce_seconds: 5
    default_batch_size: null  # null = 不批量
```

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | EventAggregator debounce/batch 逻辑 | pytest + asyncio |
| 单元测试 | DBChangeEvent 解析、DBChangeTriggerConfig 验证 | pytest |
| 集成测试 | PostgresNotifyAdapter + 真实 PostgreSQL | testcontainers |
| 集成测试 | NOTIFY → Aggregator → GovernanceCheck → AgentRun | 端到端 mock |
| 性能测试 | 100+ events/s 聚合吞吐量 | pytest-benchmark |
