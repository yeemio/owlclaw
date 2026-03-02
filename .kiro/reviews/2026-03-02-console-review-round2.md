# Console 复审报告（2026-03-02 Round 2）

## 范围
- `codex-work`（HEAD: 37233ae）
- `codex-gpt-work`（HEAD: b1c73e6）
- 对比基线：`main`（10efeb4）

## 结论
- `codex-work`: `FIX_NEEDED`
- `codex-gpt-work`: `FIX_NEEDED`

## Findings

### P0: 前后端 HTTP 契约漂移仍未修复
- 前端仍请求 `/governance?granularity=...`，后端只有 `/governance/budget`、`/governance/circuit-breakers`、`/governance/visibility-matrix`。
- 前端 Ledger query 参数仍为 `agent/capability/start_time/end_time`，后端为 `agent_id/capability_name/start_date/end_date`。
- 前端仍按 `records` 字段读取分页列表，后端返回字段为 `items`。
- 前端 Agents/Capabilities/Triggers 的解析仍与后端 `{"items": [...]}` 响应不一致。

### P0: WebSocket 消息协议不一致
- 后端 ws 推送类型：`overview` / `triggers` / `ledger`。
- 前端 ws 监听类型：`overview_update` / `trigger_event` / `ledger_new`。
- 结果：前端不会触发对应缓存更新逻辑，实时刷新路径失效。

### P1: 错误响应结构未统一
- 后端多个 404 仍使用 `HTTPException(detail=...)`，返回 `{"detail": ...}`。
- 与 Task 1.4 要求统一 `ErrorResponse`（`{"error": {...}}`）不一致。

### P1: 协作流程违规（工作区残留）
- 两个编码 worktree 均存在未提交改动（观察时点），违反 `WORKTREE_ASSIGNMENTS.md` 的零残留规则。
- 这会干扰审校与同步，增加 merge 冲突风险。

## 验证记录
- 后端：`poetry run pytest tests/unit/web tests/integration/test_console_api.py -q` -> 41 passed。
- 前端（detached 快照 b1c73e6）：
  - `npm ci`
  - `npm run build` 通过
  - `npm run test -- --run` 通过（4 passed）
- 说明：前端测试均为组件/mock 级，未覆盖与后端真实契约对齐，无法发现本次 P0 契约问题。

## 建议分配
- `codex-work`: 输出并固定后端真实契约（REST + WS + ErrorResponse），必要时补兼容适配层。
- `codex-gpt-work`: 统一改造 `useApi.ts` / `useWebSocket.ts` 作为契约映射层，严格按后端契约取数与更新缓存。
- 两分支都补“契约一致性测试”（至少 1 条端到端路径覆盖 Governance + Ledger + WS）。
