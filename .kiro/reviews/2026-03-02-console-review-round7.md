# Console 复审报告（2026-03-02 Round 7）

## 范围
- 目标提交：`codex-gpt-work@2496d56`（fix(web): align console frontend API and websocket contracts）
- 对照基线：`main@8cb09a8` + 前序审校结论（Round 6）

## 审校结论
- `codex-gpt-work`: `FIX_NEEDED`（较上轮显著改善，残留 2 个契约问题）
- `codex-work`: 本轮无新提交（维持 Round 6 结论 `FIX_NEEDED`）

## Findings（按严重度）

### P1: WebSocket overview 消息字段名仍与后端契约不一致
`codex-gpt-work` 已把消息类型改为 `overview/triggers/ledger`，但 overview 仍按 `payload.data` 取值；后端发送字段是 `payload.payload`。

证据：
- 前端读取：`owlclaw/web/frontend/src/hooks/useWebSocket.ts:43`
  - `if (payload.type === "overview" && payload.data) { ... }`
- 后端发送：`owlclaw/web/api/ws.py:74`
  - `"payload": {...}`（非 `data`）

影响：overview 实时消息到达时不会更新 query cache（类型已匹配，字段名不匹配）。

### P1: Governance budget 行字段映射仍缺失
`useGovernance` 已拆分到三个后端 endpoint，并使用 `extractItems`，但 budget item 仍按 `date/cost` 读取；后端 budget item 是 `period_start/total_cost`。

证据：
- 前端归一化：
  - `owlclaw/web/frontend/src/hooks/useApi.ts:462` `budget_trend: extractItems(budgetRaw)`
  - `owlclaw/web/frontend/src/hooks/useApi.ts:200-201` 读取 `item.date/item.cost`
- 后端契约（mock provider + API）：
  - `tests/integration/test_console_api.py:31` 返回 `period_start/total_cost`

影响：预算趋势图可能显示空日期或 0 成本，数据呈现偏差。

## Positive Changes（本轮已确认）
- 重大契约修复已到位：
  - Ledger 参数映射：`agent_id/capability_name/start_date/end_date`。
  - Ledger 响应统一消费 `items`（兼容旧 `records`）。
  - Agents/Capabilities/Triggers 已统一通过 envelope 提取（`extractItems`）。
  - WebSocket 消息类型已从旧值改为 `overview/triggers/ledger`。
- 新增前端契约测试并通过：
  - `src/__tests__/useApi.contract.test.tsx`
  - `src/__tests__/useWebSocket.contract.test.tsx`

## 验证记录
- 前端测试：
  - `npm run test -- --run`
  - 结果：`7 passed`
- 集成最小回归：
  - `poetry run pytest tests/integration/test_console_integration.py tests/integration/test_console_mount.py tests/unit/web/test_mount.py tests/unit/cli/test_console_cmd.py -q`
  - 结果：`5 passed`

## 建议
1. `useWebSocket.ts`：overview 分支改为读取 `payload.payload`（并兼容 `data` 仅作过渡）。
2. `useApi.ts`：在 governance budget 归一化中加入 `period_start -> date`、`total_cost -> cost` 映射。
3. 更新对应前端契约测试 fixture，避免继续以 `data`/`date+cost` 掩盖真实后端契约。
