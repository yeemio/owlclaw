# 消息队列触发器（Queue Trigger）使用指南

## 1. 简介

Queue Trigger 用于消费外部消息队列事件并触发 OwlClaw Agent Run。当前已支持：

- `mock`（本地/CI 验证）
- `kafka`（生产可用，aiokafka）

并预留 `rabbitmq` / `sqs` 配置位。

## 2. 快速开始

### 2.1 复制配置模板

从模板复制并按环境变量填充：

- `config/queue_trigger.example.yaml` -> `config/queue_trigger.yaml`

### 2.2 配置环境变量

在 `.env` 中填写队列与凭证（参考根目录 `.env.example` 的 Queue Trigger 段）。

### 2.3 加载并验证配置

```python
from owlclaw.triggers.queue import load_queue_trigger_config

cfg = load_queue_trigger_config("config/queue_trigger.yaml")
print(cfg)
```

### 2.4 本地最小验证（Mock）

将 `adapter.type` 设为 `mock`，并使用 `MockQueueAdapter` 注入 `QueueTrigger`，即可在无外部依赖下跑通消息消费路径。

## 3. 配置说明

### 3.1 核心字段

- `queue_name`: 队列来源标识（必填）
- `consumer_group`: 消费组（必填）
- `concurrency`: 并发 worker 数
- `ack_policy`: `ack | nack | requeue | dlq`
- `max_retries`: 触发失败重试次数
- `retry_backoff_base` / `retry_backoff_multiplier`: 指数退避参数
- `enable_dedup`: 启用幂等检查
- `idempotency_window`: 幂等窗口（秒）
- `parser_type`: `json | text | binary`

### 3.2 适配器配置

`queue_trigger.adapter.type` 可选：

- `kafka`: 需要 `aiokafka`
- `rabbitmq`: 需要 `aio-pika`
- `sqs`: 需要 `aioboto3`
- `mock`: 无外部依赖

## 4. 适配器选型建议

- Kafka: 高吞吐、可回放、分区并行场景
- RabbitMQ: 复杂路由、消息模式丰富场景
- SQS: AWS 托管、低运维场景
- Mock: 本地开发、CI、无外部服务验收

## 5. 故障排查

### 5.1 缺少适配器依赖

运行时提示缺少依赖时，按错误中的安装命令执行：

- Kafka: `poetry add aiokafka`
- RabbitMQ: `poetry add aio-pika`
- SQS: `poetry add aioboto3`

### 5.2 配置加载失败

优先检查：

- YAML 根是否是 mapping
- `queue_trigger` / `adapter` section 是否是 mapping
- `ack_policy` / `parser_type` 是否在允许枚举内
- 数值字段是否可转为 int/float

### 5.3 日志出现敏感信息

Queue Trigger 已内置日志脱敏。若业务层自定义日志输出凭证，请在业务 logger 侧增加同等脱敏策略，避免明文泄露。
