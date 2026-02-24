# 事件聚合参数调优指南

## 聚合模式判定

- 仅设置 `debounce_seconds`：debounce
- 仅设置 `batch_size`：batch
- 两者都设置：hybrid
- 都不设置：passthrough

## 推荐起步值

- 高频写入表：`debounce_seconds=1~3` + `batch_size=10~50`
- 低频关键事件：不聚合（passthrough）
- 大量瞬时更新：优先 `batch_size`，再补小 debounce

## 内存与负载保护

- `max_buffer_events`：每个 channel 聚合器缓冲上限，默认 1000。
- 超限后会丢弃最旧事件并记录 warning，避免内存持续增长。
- `max_payload_bytes`：单事件 payload 大小上限，默认 7900；超限事件直接丢弃。

## runtime 不可用时降级

- manager 会把触发请求写入本地重试队列。
- 队列满时丢弃最旧项并记录 warning。
- `retry_interval_seconds` 控制重试间隔。
