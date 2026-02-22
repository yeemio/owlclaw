# 设计文档：消息队列触发器

## 文档联动

- requirements: `.kiro/specs/triggers-queue/requirements.md`
- design: `.kiro/specs/triggers-queue/design.md`
- tasks: `.kiro/specs/triggers-queue/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

消息队列触发器系统是 OwlClaw Agent 平台的关键组件，负责从外部消息队列（Kafka、RabbitMQ、SQS 等）消费事件并触发 Agent 执行。系统采用适配器模式，提供统一的队列接入层，支持多种消息队列实现。

核心设计目标：
- **统一接口**：通过适配器模式屏蔽不同队列的实现差异
- **可靠消费**：支持 at-least-once 语义、幂等性保证和自动重试
- **可观测性**：完整的指标、日志和追踪支持
- **治理集成**：与 Governance Layer 和 Ledger 无缝集成
- **本地验证**：支持 Mock 模式，无需外部依赖即可测试

## 架构

系统采用分层架构，主要包含以下层次：

```
┌─────────────────────────────────────────────────────────┐
│                  外部消息队列                            │
│         (Kafka / RabbitMQ / SQS)                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              队列适配层 (Queue Adapter)                  │
│  - Kafka Adapter                                        │
│  - RabbitMQ Adapter                                     │
│  - SQS Adapter                                          │
│  - Mock Adapter                                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│            消息处理层 (Queue Trigger Core)               │
│  - 消息解析与封装                                        │
│  - 幂等性检查                                            │
│  - 路由与转换                                            │
└─────────┬───────────────────────┬───────────────────────┘
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│  Agent Runtime   │    │  Governance Layer    │
│  - 代理执行      │    │  - 权限验证          │
│  - 上下文管理    │    │  - 策略执行          │
└──────────────────┘    └──────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│            持久化层 (Persistence Layer)                  │
│  - 幂等性键存储                                          │
│  - 执行记录存储                                          │
│  - Ledger 审计日志                                       │
└─────────────────────────────────────────────────────────┘
```

### 关键设计决策

1. **适配器模式**：使用统一的 QueueAdapter 接口，支持多种队列实现
2. **消息封装**：将原始消息转换为统一的 MessageEnvelope 结构
3. **幂等性保证**：支持基于 message_id 和自定义 dedup_key 的幂等性
4. **重试策略**：支持可配置的重试次数、退避算法和死信队列
5. **治理集成**：所有执行请求都经过治理层验证
6. **Mock 模式**：支持无外部依赖的本地测试和验证


## 架构例外声明（实现阶段需固化）

为保证设计与实现的一致性，以下例外在本 spec 中显式声明，并要求在 Alembic 迁移与实现注释中同步固化：

1. `idempotency_keys` 表使用业务键（字符串）作为主键，不使用 `UUID` 主键。
   - 原因：去重键来源于消息系统（`dedup_key` / `message_id`），字符串主键可直接映射跨队列语义，避免二次编码。
   - 约束：必须保留 `tenant_id`，并对 `(tenant_id, expires_at)` 等查询路径建立索引。
2. `alembic_version` 属于 Alembic 系统表，不适用业务表的 `tenant_id/UUID` 约束。

除上述显式例外外，其余业务表仍严格遵循数据库五条铁律（`tenant_id`、`TIMESTAMPTZ`、索引前缀、Alembic 管理）。

## 组件和接口

### 1. QueueAdapter（队列适配器）

负责与具体消息队列交互的适配层。

```python
from typing import AsyncIterator, Protocol
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RawMessage:
    """原始队列消息"""
    message_id: str
    body: bytes
    headers: dict[str, str]
    timestamp: datetime
    metadata: dict[str, any]  # 队列特定的元数据

class QueueAdapter(Protocol):
    """队列适配器接口"""
    
    async def connect(self) -> None:
        """
        连接到消息队列
        
        Raises:
            ConnectionError: 连接失败
        """
        ...
    
    async def consume(self) -> AsyncIterator[RawMessage]:
        """
        消费消息流
        
        Yields:
            RawMessage: 原始消息
        """
        ...
    
    async def ack(self, message: RawMessage) -> None:
        """
        确认消息处理成功
        
        Args:
            message: 要确认的消息
        """
        ...
    
    async def nack(self, message: RawMessage, requeue: bool = False) -> None:
        """
        拒绝消息
        
        Args:
            message: 要拒绝的消息
            requeue: 是否重新入队
        """
        ...
    
    async def send_to_dlq(self, message: RawMessage, reason: str) -> None:
        """
        发送消息到死信队列
        
        Args:
            message: 要发送的消息
            reason: 失败原因
        """
        ...
    
    async def close(self) -> None:
        """关闭连接并释放资源"""
        ...
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 连接是否健康
        """
        ...
```

### 2. MessageEnvelope（消息封装）

统一的消息结构，屏蔽不同队列的差异。

```python
from typing import Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class MessageEnvelope:
    """统一消息封装"""
    message_id: str
    payload: Union[dict, str, bytes]
    headers: dict[str, str]
    received_at: datetime
    source: str  # 队列来源标识
    dedup_key: Optional[str] = None
    event_name: Optional[str] = None
    tenant_id: Optional[str] = None
    
    @classmethod
    def from_raw_message(
        cls,
        raw: RawMessage,
        source: str,
        parser: Optional['MessageParser'] = None
    ) -> 'MessageEnvelope':
        """
        从原始消息创建封装
        
        Args:
            raw: 原始消息
            source: 队列来源
            parser: 可选的消息解析器
        
        Returns:
            MessageEnvelope: 封装后的消息
        """
        payload = parser.parse(raw.body) if parser else raw.body
        
        return cls(
            message_id=raw.message_id,
            payload=payload,
            headers=raw.headers,
            received_at=raw.timestamp,
            source=source,
            dedup_key=raw.headers.get('x-dedup-key'),
            event_name=raw.headers.get('x-event-name'),
            tenant_id=raw.headers.get('x-tenant-id'),
        )
```


### 3. MessageParser（消息解析器）

负责解析不同格式的消息体。

```python
from typing import Union
from abc import ABC, abstractmethod
import json

class MessageParser(ABC):
    """消息解析器基类"""
    
    @abstractmethod
    def parse(self, body: bytes) -> Union[dict, str, bytes]:
        """
        解析消息体
        
        Args:
            body: 原始消息体
        
        Returns:
            解析后的数据
        
        Raises:
            ParseError: 解析失败
        """
        ...

class JSONParser(MessageParser):
    """JSON 消息解析器"""
    
    def parse(self, body: bytes) -> dict:
        try:
            return json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ParseError(f"Failed to parse JSON: {e}")

class TextParser(MessageParser):
    """文本消息解析器"""
    
    def parse(self, body: bytes) -> str:
        try:
            return body.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ParseError(f"Failed to decode text: {e}")

class BinaryParser(MessageParser):
    """二进制消息解析器"""
    
    def parse(self, body: bytes) -> bytes:
        return body
```

### 4. QueueTrigger（队列触发器核心）

负责消息消费、处理和 Agent 触发的核心组件。

```python
from typing import Optional
from dataclasses import dataclass
import asyncio
import logging

@dataclass
class QueueTriggerConfig:
    """队列触发器配置"""
    queue_name: str
    consumer_group: str
    concurrency: int = 1
    ack_policy: str = "ack"  # ack, nack, requeue, dlq
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # 秒
    retry_backoff_multiplier: float = 2.0
    idempotency_window: int = 3600  # 秒
    enable_dedup: bool = True
    parser_type: str = "json"  # json, text, binary
    event_name_header: str = "x-event-name"
    focus: Optional[str] = None

class QueueTrigger:
    """队列触发器"""
    
    def __init__(
        self,
        config: QueueTriggerConfig,
        adapter: QueueAdapter,
        agent_runtime: 'AgentRuntime',
        governance: 'GovernanceLayer',
        ledger: 'Ledger',
        idempotency_store: 'IdempotencyStore',
    ):
        self.config = config
        self.adapter = adapter
        self.agent_runtime = agent_runtime
        self.governance = governance
        self.ledger = ledger
        self.idempotency_store = idempotency_store
        self.parser = self._create_parser()
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self.logger = logging.getLogger(__name__)
    
    def _create_parser(self) -> MessageParser:
        """创建消息解析器"""
        parsers = {
            "json": JSONParser(),
            "text": TextParser(),
            "binary": BinaryParser(),
        }
        return parsers.get(self.config.parser_type, JSONParser())
    
    async def start(self) -> None:
        """启动消费"""
        if self._running:
            raise RuntimeError("Trigger is already running")
        
        self._running = True
        await self.adapter.connect()
        
        # 启动并发消费任务
        for i in range(self.config.concurrency):
            task = asyncio.create_task(self._consume_loop(worker_id=i))
            self._tasks.append(task)
        
        self.logger.info(f"Started {self.config.concurrency} consumer workers")
    
    async def stop(self) -> None:
        """停止消费"""
        self._running = False
        
        # 等待所有任务完成
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        
        await self.adapter.close()
        self.logger.info("Stopped all consumer workers")
    
    async def pause(self) -> None:
        """暂停消费"""
        self._running = False
        self.logger.info("Paused consumption")
    
    async def resume(self) -> None:
        """恢复消费"""
        self._running = True
        self.logger.info("Resumed consumption")
    
    async def health_check(self) -> dict:
        """
        健康检查
        
        Returns:
            dict: 健康状态信息
        """
        adapter_healthy = await self.adapter.health_check()
        
        return {
            "status": "healthy" if (self._running and adapter_healthy) else "unhealthy",
            "running": self._running,
            "adapter_healthy": adapter_healthy,
            "active_workers": len([t for t in self._tasks if not t.done()]),
        }
```


    async def _consume_loop(self, worker_id: int) -> None:
        """
        消费循环
        
        Args:
            worker_id: 工作线程 ID
        """
        self.logger.info(f"Worker {worker_id} started")
        
        try:
            async for raw_message in self.adapter.consume():
                if not self._running:
                    break
                
                try:
                    await self._process_message(raw_message)
                except Exception as e:
                    self.logger.error(
                        f"Worker {worker_id} failed to process message: {e}",
                        exc_info=True
                    )
                    # 继续处理下一条消息
        except Exception as e:
            self.logger.error(f"Worker {worker_id} consume loop failed: {e}", exc_info=True)
        finally:
            self.logger.info(f"Worker {worker_id} stopped")
    
    async def _process_message(self, raw_message: RawMessage) -> None:
        """
        处理单条消息
        
        Args:
            raw_message: 原始消息
        """
        start_time = asyncio.get_event_loop().time()
        trace_id = f"queue-{raw_message.message_id}"
        
        try:
            # 1. 解析消息
            envelope = MessageEnvelope.from_raw_message(
                raw_message,
                source=self.config.queue_name,
                parser=self.parser
            )
            
            self.logger.info(f"Processing message {envelope.message_id}")
            
            # 2. 幂等性检查
            if self.config.enable_dedup:
                dedup_key = envelope.dedup_key or envelope.message_id
                if await self.idempotency_store.exists(dedup_key):
                    self.logger.info(f"Message {envelope.message_id} already processed (dedup)")
                    await self.adapter.ack(raw_message)
                    return
            
            # 3. 治理层校验
            governance_result = await self.governance.check_permission(
                context={
                    "source": "queue_trigger",
                    "queue": self.config.queue_name,
                    "message_id": envelope.message_id,
                    "tenant_id": envelope.tenant_id,
                }
            )
            
            if not governance_result.allowed:
                self.logger.warning(
                    f"Message {envelope.message_id} rejected by governance: "
                    f"{governance_result.reason}"
                )
                await self._handle_governance_rejection(raw_message, envelope, governance_result)
                return
            
            # 4. 触发 Agent Run
            result = await self._trigger_agent_with_retry(envelope)
            
            # 5. 记录幂等性键
            if self.config.enable_dedup:
                dedup_key = envelope.dedup_key or envelope.message_id
                await self.idempotency_store.set(
                    dedup_key,
                    result,
                    ttl=self.config.idempotency_window
                )
            
            # 6. 确认消息
            await self.adapter.ack(raw_message)
            
            # 7. 记录到 Ledger
            duration = asyncio.get_event_loop().time() - start_time
            await self.ledger.record({
                "trace_id": trace_id,
                "message_id": envelope.message_id,
                "queue": self.config.queue_name,
                "event_name": envelope.event_name,
                "tenant_id": envelope.tenant_id,
                "status": "success",
                "duration_ms": duration * 1000,
                "agent_run_id": result.get("run_id"),
            })
            
            self.logger.info(f"Successfully processed message {envelope.message_id}")
            
        except ParseError as e:
            # 解析失败，发送到死信队列
            self.logger.error(f"Failed to parse message {raw_message.message_id}: {e}")
            await self.adapter.send_to_dlq(raw_message, reason=str(e))
            
        except Exception as e:
            # 其他错误，根据策略处理
            self.logger.error(f"Failed to process message {raw_message.message_id}: {e}")
            await self._handle_processing_error(raw_message, e)
```


    async def _trigger_agent_with_retry(self, envelope: MessageEnvelope) -> dict:
        """
        触发 Agent 执行（带重试）
        
        Args:
            envelope: 消息封装
        
        Returns:
            dict: 执行结果
        
        Raises:
            Exception: 重试耗尽后仍失败
        """
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self.agent_runtime.trigger_event(
                    event_name=envelope.event_name or "queue_message",
                    context={
                        "message": envelope.payload,
                        "headers": envelope.headers,
                        "source": envelope.source,
                        "message_id": envelope.message_id,
                        "received_at": envelope.received_at.isoformat(),
                    },
                    focus=self.config.focus,
                    tenant_id=envelope.tenant_id,
                )
                
                self.logger.info(
                    f"Agent execution succeeded for message {envelope.message_id} "
                    f"(attempt {attempt + 1})"
                )
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Agent execution failed for message {envelope.message_id} "
                    f"(attempt {attempt + 1}/{self.config.max_retries + 1}): {e}"
                )
                
                if attempt < self.config.max_retries:
                    # 计算退避延迟
                    delay = self.config.retry_backoff_base * (
                        self.config.retry_backoff_multiplier ** attempt
                    )
                    await asyncio.sleep(delay)
        
        # 重试耗尽
        raise last_error
    
    async def _handle_governance_rejection(
        self,
        raw_message: RawMessage,
        envelope: MessageEnvelope,
        governance_result: 'GovernanceResult'
    ) -> None:
        """处理治理层拒绝"""
        # 记录拒绝原因到 Ledger
        await self.ledger.record({
            "message_id": envelope.message_id,
            "queue": self.config.queue_name,
            "status": "rejected",
            "reason": governance_result.reason,
            "policies": governance_result.policies,
        })
        
        # 根据配置的 ack 策略处理
        if self.config.ack_policy == "dlq":
            await self.adapter.send_to_dlq(raw_message, reason=governance_result.reason)
        else:
            await self.adapter.ack(raw_message)
    
    async def _handle_processing_error(
        self,
        raw_message: RawMessage,
        error: Exception
    ) -> None:
        """处理消息处理错误"""
        if self.config.ack_policy == "requeue":
            await self.adapter.nack(raw_message, requeue=True)
        elif self.config.ack_policy == "dlq":
            await self.adapter.send_to_dlq(raw_message, reason=str(error))
        elif self.config.ack_policy == "nack":
            await self.adapter.nack(raw_message, requeue=False)
        else:  # ack
            await self.adapter.ack(raw_message)
```

### 5. IdempotencyStore（幂等性存储）

负责存储和查询幂等性键。

```python
from typing import Optional, Any
from abc import ABC, abstractmethod
import time

class IdempotencyStore(ABC):
    """幂等性存储接口"""
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 幂等性键
        
        Returns:
            bool: 是否存在
        """
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        设置键值
        
        Args:
            key: 幂等性键
            value: 值
            ttl: 过期时间（秒）
        """
        ...
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        获取键值
        
        Args:
            key: 幂等性键
        
        Returns:
            值，如果不存在则返回 None
        """
        ...

class RedisIdempotencyStore(IdempotencyStore):
    """基于 Redis 的幂等性存储"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def exists(self, key: str) -> bool:
        return await self.redis.exists(f"idempotency:{key}")
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self.redis.setex(
            f"idempotency:{key}",
            ttl,
            json.dumps(value)
        )
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(f"idempotency:{key}")
        return json.loads(value) if value else None
```


### 6. MockQueueAdapter（Mock 适配器）

用于本地测试和验证的 Mock 适配器。

```python
from typing import AsyncIterator
import asyncio
from collections import deque

class MockQueueAdapter(QueueAdapter):
    """Mock 队列适配器"""
    
    def __init__(self):
        self._messages: deque[RawMessage] = deque()
        self._connected = False
        self._acked: list[str] = []
        self._nacked: list[str] = []
        self._dlq: list[tuple[RawMessage, str]] = []
    
    async def connect(self) -> None:
        self._connected = True
    
    async def consume(self) -> AsyncIterator[RawMessage]:
        while self._connected:
            if self._messages:
                yield self._messages.popleft()
            else:
                await asyncio.sleep(0.1)
    
    async def ack(self, message: RawMessage) -> None:
        self._acked.append(message.message_id)
    
    async def nack(self, message: RawMessage, requeue: bool = False) -> None:
        self._nacked.append(message.message_id)
        if requeue:
            self._messages.append(message)
    
    async def send_to_dlq(self, message: RawMessage, reason: str) -> None:
        self._dlq.append((message, reason))
    
    async def close(self) -> None:
        self._connected = False
    
    async def health_check(self) -> bool:
        return self._connected
    
    # 测试辅助方法
    def enqueue(self, message: RawMessage) -> None:
        """添加消息到队列"""
        self._messages.append(message)
    
    def get_acked(self) -> list[str]:
        """获取已确认的消息 ID"""
        return self._acked.copy()
    
    def get_nacked(self) -> list[str]:
        """获取已拒绝的消息 ID"""
        return self._nacked.copy()
    
    def get_dlq(self) -> list[tuple[RawMessage, str]]:
        """获取死信队列中的消息"""
        return self._dlq.copy()
```

## 数据模型

### 幂等性键表 (idempotency_keys)

```sql
CREATE TABLE idempotency_keys (
  key VARCHAR(255) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  value JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_idempotency_keys_tenant_expires
  ON idempotency_keys (tenant_id, expires_at);
```

### 执行记录表 (queue_executions)

```sql
CREATE TABLE queue_executions (
  id UUID PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  message_id VARCHAR(255) NOT NULL,
  queue_name VARCHAR(255) NOT NULL,
  event_name VARCHAR(255),
  status VARCHAR(20) NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  duration_ms INTEGER,
  agent_run_id UUID,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0
);

CREATE INDEX idx_queue_executions_tenant_message_id
  ON queue_executions (tenant_id, message_id);
CREATE INDEX idx_queue_executions_tenant_queue_started
  ON queue_executions (tenant_id, queue_name, started_at DESC);
CREATE INDEX idx_queue_executions_tenant_status
  ON queue_executions (tenant_id, status);
```

### 监控指标表 (queue_metrics)

```sql
CREATE TABLE queue_metrics (
  id UUID PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
  queue_name VARCHAR(255) NOT NULL,
  metric_name VARCHAR(100) NOT NULL,
  metric_value DOUBLE PRECISION NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tags JSONB
);

CREATE INDEX idx_queue_metrics_tenant_metric_time
  ON queue_metrics (tenant_id, queue_name, metric_name, timestamp DESC);
```


## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：适配器接口一致性

*对于任意*队列适配器实现，切换不同的适配器时，业务侧调用的 API 接口应该保持不变，且所有核心方法（connect、consume、ack、nack、close）都应该可用。

**验证需求：1.3**

### 属性 2：消息封装完整性

*对于任意*原始队列消息，转换为 MessageEnvelope 后应该包含所有必需字段（message_id、payload、headers、received_at、source），且字段值应该正确映射自原始消息。

**验证需求：3.1, 3.2**

### 属性 3：多格式消息解析

*对于任意*有效的 JSON、文本或二进制格式消息，系统应该能够根据配置的解析器类型正确解析，且解析后的数据应该保留原始信息。

**验证需求：3.3**

### 属性 4：解析失败路由到死信

*对于任意*无法解析的消息，系统应该将其标记为失败并路由到死信队列，且死信队列中应该包含失败原因。

**验证需求：3.4**

### 属性 5：配置正确应用

*对于任意*有效的队列触发器配置（queue_name、consumer_group、concurrency、ack_policy 等），系统启动后应该按照配置运行，且配置参数应该在运行时生效。

**验证需求：2.1**

### 属性 6：生命周期状态转换

*对于任意*队列触发器实例，调用 start、pause、resume、stop 方法应该正确转换系统状态，且状态查询应该返回当前的运行状态。

**验证需求：2.2, 2.4**

### 属性 7：错误恢复与继续处理

*对于任意*消息处理异常，系统应该记录错误日志并继续处理后续消息，不应该因为单条消息失败而停止整个消费流程。

**验证需求：2.5**

### 属性 8：Agent 触发与上下文传递

*对于任意*有效的消息封装，系统应该调用 agent_runtime.trigger_event() 启动 Agent Run，且传递的上下文应该包含完整的消息信息（message、headers、source、message_id、received_at）。

**验证需求：4.1, 4.2**

### 属性 9：消息路由正确性

*对于任意*包含 event_name 的消息，系统应该根据消息头或配置将其路由到正确的事件名称，且 focus 参数应该被正确传递给 Agent Runtime。

**验证需求：4.3, 4.4**

### 属性 10：治理层集成与拒绝处理

*对于任意*消息，系统应该在执行前调用 Governance Layer 进行校验，且当治理层拒绝时，系统应该根据配置的 ack_policy 处理消息并记录拒绝原因。

**验证需求：4.5, 7.1, 7.4**

### 属性 11：Ack 策略正确执行

*对于任意*配置的 ack 策略（ack、nack、requeue、dlq），系统应该在消息处理成功或失败后执行相应的确认操作，且操作应该符合策略定义。

**验证需求：5.1**

### 属性 12：重试机制正确性

*对于任意*可重试的失败，系统应该根据配置的重试策略（max_retries、backoff_base、backoff_multiplier）进行重试，且重试延迟应该遵循指数退避算法。

**验证需求：5.2, 5.3**

### 属性 13：重试耗尽后死信处理

*对于任意*重试次数耗尽的消息，系统应该将其发送到死信队列，且死信队列中应该包含失败原因和重试历史。

**验证需求：5.4**

### 属性 14：重试日志完整性

*对于任意*触发重试的消息，系统应该记录每次重试的尝试次数、时间和失败原因，且日志应该包含完整的重试历史。

**验证需求：5.5**

### 属性 15：幂等性保证

*对于任意*幂等性键（dedup_key 或 message_id），使用相同幂等性键发送多次消息应该只触发一次 Agent 执行，且后续的重复消息应该被跳过并确认。

**验证需求：6.1, 6.2, 6.3**

### 属性 16：幂等性窗口期

*对于任意*配置的幂等窗口期，幂等性键应该在窗口期内有效，且窗口期过期后相同的键应该可以重新执行。

**验证需求：6.5**

### 属性 17：去重计数准确性

*对于任意*被去重的消息，系统应该增加去重命中计数器，且查询指标时应该返回准确的去重次数。

**验证需求：6.4**


### 属性 18：Ledger 审计记录完整性

*对于任意*处理的消息，系统应该将关键上下文（trace_id、message_id、queue、event_name、tenant_id、status、duration_ms、agent_run_id）写入 Ledger，且记录应该包含完整的执行信息。

**验证需求：7.2**

### 属性 19：监控指标记录

*对于任意*处理的消息，系统应该记录相关的监控指标（消费延迟、执行耗时、LLM 调用次数），且查询指标时应该返回准确的统计数据。

**验证需求：7.3, 8.1, 8.2, 8.3**

### 属性 20：多租户隔离

*对于任意*包含 tenant_id 的消息，系统应该在执行时正确传递租户标识，且不同租户的消息应该被正确隔离处理。

**验证需求：7.5**

### 属性 21：日志记录完整性

*对于任意*处理的消息，系统应该记录所有关键阶段的日志（消费、解析、执行、确认），且每条日志应该包含 trace_id 用于追踪。

**验证需求：8.5**

### 属性 22：健康检查准确性

*对于任意*时刻，调用健康检查接口应该返回系统的当前状态（running、adapter_healthy、active_workers），且状态应该准确反映系统的实际运行情况。

**验证需求：2.4, 8.4**

### 属性 23：凭证安全性

*对于任意*日志输出，日志内容应该不包含敏感凭证（密码、API key、token），即使在调试模式下也应该脱敏或省略。

**验证需求：9.2**

### 属性 24：优雅关闭

*对于任意*运行中的队列触发器，调用 stop 方法应该等待所有正在处理的消息完成，然后释放所有连接和资源，不应该丢失正在处理的消息。

**验证需求：2.3**

## 错误处理

### 1. 连接失败

**场景**：无法连接到消息队列、网络故障、认证失败

**处理策略**：
- 启动时验证：在 start() 方法中调用 adapter.connect()
- 抛出明确错误：ConnectionError 包含失败原因
- 不自动重试：由上层决定是否重试启动
- 记录错误日志：包含队列地址和错误详情

**实现**：
```python
async def start(self) -> None:
    try:
        await self.adapter.connect()
    except Exception as e:
        self.logger.error(f"Failed to connect to queue: {e}")
        raise ConnectionError(f"Cannot connect to {self.config.queue_name}: {e}")
```

### 2. 消息解析失败

**场景**：消息格式错误、编码问题、JSON 解析失败

**处理策略**：
- 捕获 ParseError：不影响其他消息处理
- 发送到死信队列：保留原始消息和错误原因
- 记录错误日志：包含消息 ID 和解析错误详情
- 继续处理：不中断消费流程

**实现**：
```python
try:
    envelope = MessageEnvelope.from_raw_message(raw_message, ...)
except ParseError as e:
    self.logger.error(f"Failed to parse message {raw_message.message_id}: {e}")
    await self.adapter.send_to_dlq(raw_message, reason=str(e))
    return  # 继续处理下一条消息
```

### 3. Agent 执行失败

**场景**：Agent Runtime 不可用、执行超时、业务逻辑错误

**处理策略**：
- 自动重试：根据配置的重试策略
- 指数退避：避免过度重试
- 重试耗尽后：根据 ack_policy 处理（dlq/nack/ack）
- 记录重试历史：每次重试都记录日志

**实现**：
```python
async def _trigger_agent_with_retry(self, envelope: MessageEnvelope) -> dict:
    for attempt in range(self.config.max_retries + 1):
        try:
            return await self.agent_runtime.trigger_event(...)
        except Exception as e:
            self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < self.config.max_retries:
                delay = self.config.retry_backoff_base * (
                    self.config.retry_backoff_multiplier ** attempt
                )
                await asyncio.sleep(delay)
    raise  # 重试耗尽
```

### 4. 治理层拒绝

**场景**：权限不足、配额超限、策略限制

**处理策略**：
- 不重试：治理拒绝通常不是临时错误
- 记录拒绝原因：写入 Ledger
- 根据策略处理：ack 或 dlq
- 不影响其他消息：继续处理

**实现**：
```python
if not governance_result.allowed:
    await self.ledger.record({
        "message_id": envelope.message_id,
        "status": "rejected",
        "reason": governance_result.reason,
    })
    
    if self.config.ack_policy == "dlq":
        await self.adapter.send_to_dlq(raw_message, reason=governance_result.reason)
    else:
        await self.adapter.ack(raw_message)
    return
```

### 5. 幂等性存储失败

**场景**：Redis 不可用、网络超时、存储满

**处理策略**：
- 降级运行：禁用幂等性检查，继续处理
- 记录警告日志：说明幂等性不可用
- 不影响消息处理：消息仍然被处理
- 可能重复执行：接受 at-least-once 语义

**实现**：
```python
if self.config.enable_dedup:
    try:
        if await self.idempotency_store.exists(dedup_key):
            # 跳过重复消息
            return
    except Exception as e:
        self.logger.warning(f"Idempotency check failed: {e}, continuing without dedup")
        # 继续处理，接受可能的重复
```

### 6. 进程关闭

**场景**：正常关闭、异常退出、信号终止

**处理策略**：
- 优雅关闭：等待正在处理的消息完成
- 设置超时：避免无限等待
- 释放资源：关闭适配器连接
- 记录关闭日志：包含未完成的消息数

**实现**：
```python
async def stop(self) -> None:
    self._running = False
    
    # 等待所有任务完成（带超时）
    if self._tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._tasks, return_exceptions=True),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            self.logger.warning("Some tasks did not complete within timeout")
    
    await self.adapter.close()
    self.logger.info("Gracefully stopped")
```


## 测试策略

### 测试方法

我们采用双重测试方法：

1. **单元测试**：验证特定示例、边界情况和错误条件
2. **属性测试**：验证跨所有输入的通用属性

两者是互补的，对于全面覆盖都是必要的。单元测试捕获具体的 bug，属性测试验证一般正确性。

### 单元测试重点

单元测试应该专注于：
- 特定的示例场景（如特定的消息格式）
- 组件之间的集成点（如与 Agent Runtime 的交互）
- 边界情况（如空消息、超大消息）
- 错误条件（如网络故障、超时）

避免编写过多的单元测试 - 属性测试已经处理了大量输入覆盖。

### 基于属性的测试

使用 **Hypothesis**（Python）作为属性测试库。

**配置要求**：
- 每个属性测试最少运行 100 次迭代
- 每个测试必须引用设计文档中的属性
- 标签格式：**Feature: triggers-queue, Property {number}: {property_text}**

**测试覆盖**：
- 适配器接口一致性
- 消息解析和封装
- 幂等性保证
- 重试机制
- 治理层集成
- 错误处理和恢复
- 日志记录和监控

### 示例属性测试

```python
from hypothesis import given, strategies as st
import pytest

# Feature: triggers-queue, Property 2: 消息封装完整性
@given(
    message_id=st.text(min_size=1),
    body=st.binary(),
    headers=st.dictionaries(st.text(), st.text()),
)
def test_property_message_envelope_completeness(message_id, body, headers):
    """
    属性 2：对于任意原始消息，转换后应该包含所有必需字段
    """
    raw_message = RawMessage(
        message_id=message_id,
        body=body,
        headers=headers,
        timestamp=datetime.now(),
        metadata={}
    )
    
    envelope = MessageEnvelope.from_raw_message(
        raw_message,
        source="test-queue",
        parser=BinaryParser()
    )
    
    assert envelope.message_id == message_id
    assert envelope.payload == body
    assert envelope.headers == headers
    assert envelope.received_at is not None
    assert envelope.source == "test-queue"

# Feature: triggers-queue, Property 15: 幂等性保证
@given(
    dedup_key=st.text(min_size=1),
    message_count=st.integers(min_value=2, max_value=10),
)
@pytest.mark.asyncio
async def test_property_idempotency_guarantee(dedup_key, message_count):
    """
    属性 15：对于任意幂等性键，多次发送应该只执行一次
    """
    # 设置
    store = RedisIdempotencyStore(redis_client)
    execution_count = 0
    
    async def mock_agent_runtime(context):
        nonlocal execution_count
        execution_count += 1
        return {"run_id": "test"}
    
    # 发送多条相同 dedup_key 的消息
    for i in range(message_count):
        message = create_test_message(dedup_key=dedup_key)
        
        # 检查幂等性
        if await store.exists(dedup_key):
            continue  # 跳过
        
        # 执行
        result = await mock_agent_runtime({})
        await store.set(dedup_key, result, ttl=3600)
    
    # 验证只执行了一次
    assert execution_count == 1

# Feature: triggers-queue, Property 12: 重试机制正确性
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    backoff_base=st.floats(min_value=0.1, max_value=2.0),
    backoff_multiplier=st.floats(min_value=1.5, max_value=3.0),
)
@pytest.mark.asyncio
async def test_property_retry_mechanism_correctness(
    max_retries,
    backoff_base,
    backoff_multiplier
):
    """
    属性 12：对于任意重试配置，重试延迟应该遵循指数退避
    """
    config = QueueTriggerConfig(
        queue_name="test",
        consumer_group="test",
        max_retries=max_retries,
        retry_backoff_base=backoff_base,
        retry_backoff_multiplier=backoff_multiplier,
    )
    
    retry_delays = []
    
    # 模拟重试
    for attempt in range(max_retries):
        delay = backoff_base * (backoff_multiplier ** attempt)
        retry_delays.append(delay)
    
    # 验证延迟递增
    for i in range(len(retry_delays) - 1):
        assert retry_delays[i + 1] > retry_delays[i]
    
    # 验证符合指数退避公式
    for i, delay in enumerate(retry_delays):
        expected = backoff_base * (backoff_multiplier ** i)
        assert abs(delay - expected) < 0.001
```

### 集成测试

集成测试验证系统与外部组件的交互：

1. **与 Agent Runtime 集成**
   - 使用 Mock Agent Runtime
   - 验证触发请求的正确性
   - 测试超时和错误处理

2. **与 Governance Layer 集成**
   - 使用 Mock Governance Layer
   - 验证权限检查和策略限制
   - 测试拒绝场景

3. **与队列集成**
   - 使用 Mock Queue Adapter
   - 验证消息消费和确认
   - 测试并发消费

### 端到端测试

使用 Mock 模式进行端到端测试：

```python
@pytest.mark.asyncio
async def test_end_to_end_message_processing():
    """端到端测试：从消息接收到 Agent 执行"""
    # 设置
    mock_adapter = MockQueueAdapter()
    mock_runtime = MockAgentRuntime()
    mock_governance = MockGovernanceLayer()
    mock_ledger = MockLedger()
    mock_store = MockIdempotencyStore()
    
    config = QueueTriggerConfig(
        queue_name="test-queue",
        consumer_group="test-group",
        concurrency=1,
    )
    
    trigger = QueueTrigger(
        config=config,
        adapter=mock_adapter,
        agent_runtime=mock_runtime,
        governance=mock_governance,
        ledger=mock_ledger,
        idempotency_store=mock_store,
    )
    
    # 添加测试消息
    test_message = RawMessage(
        message_id="test-001",
        body=b'{"action": "test"}',
        headers={"x-event-name": "test_event"},
        timestamp=datetime.now(),
        metadata={},
    )
    mock_adapter.enqueue(test_message)
    
    # 启动触发器
    await trigger.start()
    
    # 等待处理
    await asyncio.sleep(0.5)
    
    # 停止触发器
    await trigger.stop()
    
    # 验证
    assert "test-001" in mock_adapter.get_acked()
    assert len(mock_runtime.get_triggered_events()) == 1
    assert len(mock_ledger.get_records()) == 1
```

### 测试覆盖率目标

- 代码覆盖率：≥ 80%
- 属性测试：覆盖所有 24 个正确性属性
- 集成测试：覆盖所有外部接口
- 端到端测试：覆盖核心消费流程


## 配置管理

### 配置文件格式

使用 YAML 格式配置队列触发器：

```yaml
# config/queue_trigger.yaml

queue_trigger:
  # 队列配置
  queue_name: "agent-events"
  consumer_group: "owlclaw-agents"
  concurrency: 4
  
  # 适配器配置
  adapter:
    type: "kafka"  # kafka, rabbitmq, sqs, mock
    connection:
      brokers: "${KAFKA_BROKERS}"
      security_protocol: "SASL_SSL"
      sasl_mechanism: "PLAIN"
      sasl_username: "${KAFKA_USERNAME}"
      sasl_password: "${KAFKA_PASSWORD}"
  
  # 消息解析
  parser_type: "json"  # json, text, binary
  
  # Ack 策略
  ack_policy: "requeue"  # ack, nack, requeue, dlq
  
  # 重试配置
  max_retries: 3
  retry_backoff_base: 1.0
  retry_backoff_multiplier: 2.0
  
  # 幂等性配置
  enable_dedup: true
  idempotency_window: 3600  # 秒
  
  # 路由配置
  event_name_header: "x-event-name"
  focus: null  # 可选的 Skills 范围限制
  
  # 监控配置
  metrics:
    enabled: true
    export_interval: 60  # 秒
```

### 环境变量

推荐使用环境变量存储敏感信息：

```bash
# .env

# Kafka 配置
KAFKA_BROKERS=broker1:9092,broker2:9092
KAFKA_USERNAME=owlclaw
KAFKA_PASSWORD=secret

# Redis 配置（幂等性存储）
REDIS_URL=redis://localhost:6379/0

# Agent Runtime
AGENT_RUNTIME_URL=http://localhost:8000
```

### 配置加载

```python
import os
import yaml
from typing import Dict, Any

def load_queue_trigger_config(config_path: str) -> QueueTriggerConfig:
    """
    加载队列触发器配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        QueueTriggerConfig 对象
    """
    # 读取配置文件
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    queue_config = config_dict.get('queue_trigger', {})
    
    # 替换环境变量
    queue_config = _replace_env_vars(queue_config)
    
    # 创建配置对象
    return QueueTriggerConfig(
        queue_name=queue_config.get('queue_name'),
        consumer_group=queue_config.get('consumer_group'),
        concurrency=queue_config.get('concurrency', 1),
        ack_policy=queue_config.get('ack_policy', 'ack'),
        max_retries=queue_config.get('max_retries', 3),
        retry_backoff_base=queue_config.get('retry_backoff_base', 1.0),
        retry_backoff_multiplier=queue_config.get('retry_backoff_multiplier', 2.0),
        idempotency_window=queue_config.get('idempotency_window', 3600),
        enable_dedup=queue_config.get('enable_dedup', True),
        parser_type=queue_config.get('parser_type', 'json'),
        event_name_header=queue_config.get('event_name_header', 'x-event-name'),
        focus=queue_config.get('focus'),
    )

def _replace_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """替换配置中的环境变量"""
    import re
    
    def replace_value(value):
        if isinstance(value, str):
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                env_value = os.getenv(var_name, '')
                value = value.replace(f'${{{var_name}}}', env_value)
            return value
        elif isinstance(value, dict):
            return {k: replace_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [replace_value(item) for item in value]
        else:
            return value
    
    return replace_value(config)
```

### 配置验证

```python
def validate_config(config: QueueTriggerConfig) -> list[str]:
    """
    验证配置的合法性
    
    Args:
        config: 队列触发器配置
    
    Returns:
        错误列表，如果为空则配置有效
    """
    errors = []
    
    # 检查必需字段
    if not config.queue_name:
        errors.append("queue_name is required")
    if not config.consumer_group:
        errors.append("consumer_group is required")
    
    # 检查并发度
    if config.concurrency <= 0:
        errors.append(f"concurrency must be positive, got {config.concurrency}")
    
    # 检查 ack 策略
    valid_policies = ["ack", "nack", "requeue", "dlq"]
    if config.ack_policy not in valid_policies:
        errors.append(f"ack_policy must be one of {valid_policies}, got {config.ack_policy}")
    
    # 检查重试配置
    if config.max_retries < 0:
        errors.append(f"max_retries must be non-negative, got {config.max_retries}")
    if config.retry_backoff_base <= 0:
        errors.append(f"retry_backoff_base must be positive, got {config.retry_backoff_base}")
    if config.retry_backoff_multiplier < 1:
        errors.append(f"retry_backoff_multiplier must be >= 1, got {config.retry_backoff_multiplier}")
    
    # 检查幂等窗口期
    if config.idempotency_window <= 0:
        errors.append(f"idempotency_window must be positive, got {config.idempotency_window}")
    
    # 检查解析器类型
    valid_parsers = ["json", "text", "binary"]
    if config.parser_type not in valid_parsers:
        errors.append(f"parser_type must be one of {valid_parsers}, got {config.parser_type}")
    
    return errors
```

## 部署考虑

### 1. 队列选型

#### Kafka（推荐用于高吞吐场景）

- **优点**：
  - 高吞吐量和低延迟
  - 持久化和可靠性
  - 分区和并行消费
  - 成熟的生态系统

- **缺点**：
  - 运维复杂度较高
  - 资源消耗较大

- **适用场景**：
  - 大规模消息处理
  - 需要消息持久化
  - 需要消息回溯

#### RabbitMQ（推荐用于灵活路由场景）

- **优点**：
  - 灵活的路由和交换机
  - 丰富的消息模式
  - 易于部署和管理
  - 良好的管理界面

- **缺点**：
  - 吞吐量相对较低
  - 持久化性能一般

- **适用场景**：
  - 中等规模消息处理
  - 需要复杂路由
  - 需要多种消息模式

#### AWS SQS（推荐用于云原生场景）

- **优点**：
  - 完全托管，无需运维
  - 自动扩展
  - 与 AWS 生态集成
  - 按使用付费

- **缺点**：
  - 延迟相对较高
  - 功能相对简单
  - 依赖 AWS

- **适用场景**：
  - AWS 云环境
  - 无运维需求
  - 中小规模消息处理

### 2. 并发配置

根据消息处理耗时和吞吐量需求配置并发度：

```python
# 计算建议并发度
def calculate_concurrency(
    target_throughput: int,  # 目标吞吐量（msg/s）
    avg_processing_time: float,  # 平均处理时间（秒）
) -> int:
    """
    计算建议的并发度
    
    Args:
        target_throughput: 目标吞吐量（消息/秒）
        avg_processing_time: 平均处理时间（秒）
    
    Returns:
        建议的并发度
    """
    # 并发度 = 目标吞吐量 × 平均处理时间
    concurrency = int(target_throughput * avg_processing_time)
    
    # 至少为 1，最多为 CPU 核心数的 2 倍
    import multiprocessing
    max_concurrency = multiprocessing.cpu_count() * 2
    
    return max(1, min(concurrency, max_concurrency))

# 示例
# 目标：500 msg/min = 8.33 msg/s
# 平均处理时间：2 秒
# 建议并发度：8.33 * 2 ≈ 17
```

### 3. 资源配置

#### 内存

```python
# 估算内存需求
def estimate_memory(
    concurrency: int,
    avg_message_size: int,  # 字节
    buffer_size: int = 100,  # 每个 worker 的缓冲区大小
) -> int:
    """
    估算内存需求（MB）
    
    Args:
        concurrency: 并发度
        avg_message_size: 平均消息大小（字节）
        buffer_size: 每个 worker 的缓冲区大小
    
    Returns:
        估算的内存需求（MB）
    """
    # 基础内存（Python 运行时）
    base_memory = 100  # MB
    
    # 消息缓冲区内存
    buffer_memory = (concurrency * buffer_size * avg_message_size) / (1024 * 1024)
    
    # 幂等性存储内存（Redis）
    idempotency_memory = 50  # MB
    
    # 总内存（加 50% 余量）
    total_memory = (base_memory + buffer_memory + idempotency_memory) * 1.5
    
    return int(total_memory)
```

#### CPU

- 建议：并发度 ≤ CPU 核心数 × 2
- I/O 密集型任务可以更高
- CPU 密集型任务应该更低

### 4. 监控和告警

#### Prometheus 指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
queue_messages_consumed = Counter(
    'queue_messages_consumed_total',
    'Total number of messages consumed',
    ['queue', 'status']
)

queue_processing_duration = Histogram(
    'queue_processing_duration_seconds',
    'Time spent processing messages',
    ['queue']
)

queue_active_workers = Gauge(
    'queue_active_workers',
    'Number of active consumer workers',
    ['queue']
)

queue_dedup_hits = Counter(
    'queue_dedup_hits_total',
    'Total number of deduplication hits',
    ['queue']
)

# 在代码中使用
queue_messages_consumed.labels(queue=self.config.queue_name, status='success').inc()
queue_processing_duration.labels(queue=self.config.queue_name).observe(duration)
```

#### 告警规则

```yaml
# prometheus-alerts.yaml

groups:
- name: queue_trigger
  rules:
  - alert: QueueHighFailureRate
    expr: rate(queue_messages_consumed_total{status="failed"}[5m]) / rate(queue_messages_consumed_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Queue trigger failure rate is high"
      description: "{{ $value | humanizePercentage }} of messages are failing"

  - alert: QueueConsumerLag
    expr: queue_consumer_lag > 1000
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Queue consumer lag is high"
      description: "{{ $value }} messages are lagging"

  - alert: QueueNoActiveWorkers
    expr: queue_active_workers == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "No active queue consumer workers"
      description: "All consumer workers are down"
```

### 5. 安全考虑

#### 凭证管理

- 使用环境变量或密钥管理服务存储凭证
- 定期轮换凭证
- 为不同环境使用不同的凭证
- 限制凭证的权限（最小权限原则）

#### 网络安全

- 使用 TLS/SSL 加密连接
- 配置防火墙规则
- 使用 VPN 或专用网络
- 启用 IP 白名单（如果队列支持）

#### 日志安全

- 脱敏敏感信息（密码、token）
- 限制日志访问权限
- 定期清理旧日志
- 使用安全的日志传输（TLS）

## 总结

消息队列触发器系统为 OwlClaw Agent 提供了可靠的事件驱动能力，使得 Agent 能够：

1. **统一接入**：通过适配器模式支持多种消息队列
2. **可靠消费**：at-least-once 语义、幂等性保证和自动重试
3. **治理集成**：所有执行都经过治理层验证和审计
4. **可观测性**：完整的指标、日志和追踪支持
5. **本地验证**：Mock 模式支持无外部依赖的测试

通过分层架构、错误处理、配置管理和监控告警，该系统在提供强大功能的同时，保持了系统的稳定性和可维护性。

---

**维护者**：平台研发
**最后更新**：2026-02-22
