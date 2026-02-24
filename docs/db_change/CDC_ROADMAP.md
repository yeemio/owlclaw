# CDC 扩展路线图

## 当前状态

当前版本提供 `DebeziumAdapter` 接口占位与 `DebeziumConfig` 模型，用于定义 CDC 扩展边界，不包含生产实现。

## 设计边界

- `DBChangeAdapter` 是统一事件输入接口。
- `PostgresNotifyAdapter` 作为首个实现。
- `DebeziumAdapter` 仅声明配置与生命周期，避免核心层绑定具体供应商。

## 后续实现建议

1. 增加 Kafka consumer（按 connector topic 订阅）。
2. 标准化 Debezium envelope 到 `DBChangeEvent`。
3. 接入断点续消费与 offset 持久化。
4. 增加 CDC lag 与重放失败指标。

## 兼容策略

- 业务层保持 `@app.db_change` 与 `app.trigger(db_change(...))` 不变。
- 通过 `source` 与 adapter 选择实现，不改变上层 API。
