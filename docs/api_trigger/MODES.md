# 同步与异步模式选择

## 同步模式（`response_mode=sync`）

- API 请求等待 Agent 执行结果
- 成功 `200`
- 超时 `408`（由 `sync_timeout_seconds` 控制）
- 适合：调用方必须立即拿到结果

## 异步模式（`response_mode=async`）

- 立即返回 `202` + `run_id`
- 响应头带 `Location: /runs/{run_id}/result`
- 适合：长耗时任务、削峰场景

## 结果查询

```http
GET /runs/{run_id}/result
```

返回：
- `pending`
- `completed` + `result`
- `failed` + `error`
