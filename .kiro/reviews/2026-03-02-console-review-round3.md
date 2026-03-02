# Console 增量复审（2026-03-02 Round 3）

## 本轮变化
- `codex-work` 新增提交：`cc968ad`（SPEC_TASKS_SCAN 冲突解决）
- `codex-gpt-work` 新增提交：`7b85127`（SPEC_TASKS_SCAN 冲突解决）
- 两分支本轮无 console 代码修复提交。

## 结论
- `codex-work`: `FIX_NEEDED`（保持）
- `codex-gpt-work`: `FIX_NEEDED`（保持）

## 关键阻塞（未变化）
1. HTTP 契约漂移仍在：
   - 前端仍请求 `/governance?granularity=...`；后端仍是 `/governance/budget|circuit-breakers|visibility-matrix`。
   - 前端 ledger 参数仍为 `agent/capability/start_time/end_time`；后端仍为 `agent_id/capability_name/start_date/end_date`。
   - 前端分页仍按 `records`；后端分页仍返回 `items`。
2. WebSocket 协议不一致：
   - 前端监听 `overview_update|ledger_new|trigger_event`
   - 后端发送 `overview|triggers|ledger`
3. 404 错误结构未统一 ErrorResponse：仍有 `HTTPException(detail=...)`。

## 说明
- 本轮新提交仅文档冲突处理，不涉及上述代码路径，故判定不变。
