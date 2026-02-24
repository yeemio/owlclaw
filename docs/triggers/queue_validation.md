# Queue Trigger Mock 验证步骤

## 目标

验证 Queue Trigger 在无外部服务（Kafka/RabbitMQ/SQS）的情况下，使用 `MockQueueAdapter` 能完整跑通：

- 消息消费与解析
- 幂等去重
- Agent 触发
- Ledger 记录
- ACK 与健康状态统计

## 前置条件

1. 已安装依赖：`poetry install`
2. 当前目录在仓库根目录

## 执行步骤

运行本地验证脚本：

```bash
poetry run python scripts/test_queue_trigger.py
```

## 预期结果

命令退出码为 `0`，并在日志中看到：

- `QueueTrigger mock validation PASSED`
- `Runtime calls: 1`
- `Acked IDs: ['msg-1', 'msg-2']`
- `DLQ entries: []`
- 健康快照中 `dedup_hits` 为 `1`

## 失败排查

### 1. 依赖未安装

现象：`ModuleNotFoundError` 或 `ImportError`

处理：执行 `poetry install` 后重试。

### 2. 断言失败（退出码 1）

现象：日志出现 `QueueTrigger mock validation FAILED`

处理：

- 检查 `QueueTrigger` 配置是否被改动（`ack_policy`、`enable_dedup`）
- 检查 `MockQueueAdapter` 的 `ack/nack/dlq` 语义是否被改动
- 检查 `QueueTrigger._process_envelope` 的幂等逻辑是否仍基于 `dedup_key/message_id`

### 3. 日志输出异常

若日志中出现敏感信息（token/password），优先检查 `owlclaw/triggers/queue/security.py` 的脱敏规则以及 logger filter 是否仍在触发器模块注册。
