# Console 复审报告（2026-03-02 Round 5）

## 范围
- 目标提交：
  - `codex-work@d68bacd`（fix(web): align console backend error and contract coverage）
  - `codex-work@e0946c8`（chore(governance): normalize spec scan checkpoint and error envelope coverage）
  - `codex-gpt-work@38d23a6`（feat(web): complete console-integration task 0-4）
- 对照基线：`main@8cb09a8`

## 审校结论
- `codex-work`: `FIX_NEEDED`
- `codex-gpt-work`: `FIX_NEEDED`

## Findings（按严重度）

### P0（codex-work）: 前端消费契约仍与后端不一致，页面将出现运行时错误或空白
`codex-work` 后端已统一 envelope（`{"items": [...]}`），但前端 hooks/pages 仍把多处响应当“数组根对象”使用。

证据：
- 前端仍按数组根对象声明：
  - `owlclaw/web/frontend/src/hooks/useApi.ts`：`useAgents/useCapabilities/useTriggers` 直接 `apiFetch<Array<...>>("/agents|/capabilities|/triggers")`
  - `owlclaw/web/frontend/src/hooks/useApi.ts:16`：`/governance/budget` 返回被声明为 `Array<{ period_start,total_cost }>`
- 页面层直接数组 map：
  - `owlclaw/web/frontend/src/pages/Agents.tsx:8`
  - `owlclaw/web/frontend/src/pages/Capabilities.tsx:23`
  - `owlclaw/web/frontend/src/pages/Triggers.tsx:13`
  - `owlclaw/web/frontend/src/pages/Governance.tsx:24`
  - `owlclaw/web/frontend/src/components/charts/BudgetTrend.tsx:6`
- 后端真实响应：
  - `owlclaw/web/api/agents.py:24` `return {"items": items}`
  - `owlclaw/web/api/capabilities.py:27` `return {"items": items}`
  - `owlclaw/web/api/triggers.py:28` `return {"items": items}`
  - `owlclaw/web/api/governance.py:25` `/governance/budget` 返回 `{"start_date","end_date","granularity","items"}`

影响：进入 Agents/Capabilities/Triggers/Governance 页面时，`map is not a function` 风险真实存在（budget 场景同理）。该问题阻断合并。

### P1（codex-gpt-work）: WebSocket 消息字段名与后端契约不一致
`codex-gpt-work` 的消息类型已修正为 `overview/triggers/ledger`，但仍按 `payload.data` 读取 overview；后端发送字段为 `payload.payload`。

证据：
- 前端读取：`owlclaw/web/frontend/src/hooks/useWebSocket.ts:42`（`if (payload.type === "overview" && payload.data)`）
- 后端发送：`owlclaw/web/api/ws.py` 使用 `{"type": "overview", "payload": {...}}`

影响：overview 实时更新不会正确落到 query cache（虽然类型匹配，字段名不匹配导致条件不成立）。

### P1（codex-gpt-work）: Governance budget 字段归一化不完整
`useGovernance` 已拆分为三个后端 endpoint，但 `budget_trend` 归一化仍按 `{date,cost}` 读取；后端 budget item 是 `{period_start,total_cost}`，未做字段映射。

证据：
- 前端归一化：`owlclaw/web/frontend/src/hooks/useApi.ts` 中 `normalizeGovernanceSnapshot` 对 `budget_trend` 读取 `item.date/item.cost`
- 后端返回：`owlclaw/web/api/governance.py` budget rows 为 `period_start/total_cost`

影响：预算趋势图数据可能出现空日期/0 值，呈现失真。

### P1（流程）: 分支职责仍越界（需统筹确认）
当前分配文件仍声明 `codex-work` 禁止触碰前端/静态路径，但 `a91dbca` 与后续提交已修改 `owlclaw/web/frontend/**`。

证据：
- 规则：`.kiro/WORKTREE_ASSIGNMENTS.md`（`codex-work` 禁止触碰 `owlclaw/web/frontend/**`、`owlclaw/web/static/**`）
- 实际：`codex-work` 最近提交包含上述路径改动。

## Positive Changes（本轮确认已修复）
- `codex-work` 后端错误 envelope 已显著改善：
  - `owlclaw/web/api/middleware.py` 新增 `HTTPException` 与 `RequestValidationError` handler，统一输出 `{"error": ...}`。
  - 对应测试已覆盖 NOT_FOUND/VALIDATION_ERROR 场景，后端契约稳定性明显提升。

## 验证记录
- `codex-work`：
  - `poetry run pytest tests/unit/web tests/integration/test_console_api.py tests/integration/test_console_integration.py tests/integration/test_console_mount.py tests/unit/cli/test_console_cmd.py tests/unit/test_app_console_mount.py -q`
  - 结果：`50 passed`
- `codex-gpt-work`：
  - `poetry run pytest tests/integration/test_console_integration.py tests/integration/test_console_mount.py tests/unit/web/test_mount.py tests/unit/cli/test_console_cmd.py -q`
  - 结果：`5 passed`

## 建议
1. `codex-work`：先将 frontend hooks 完整改为 envelope 映射层（统一 `response.items`），再补页面契约测试（覆盖 `{"items": [...]}` 与 budget envelope）。
2. `codex-gpt-work`：修复 WS `data/payload` 字段名；在 governance budget 归一化中增加 `period_start -> date`、`total_cost -> cost` 映射。
3. 统筹确认是否继续允许 `codex-work` 触碰前端路径；若不允许，立即回收前端改动责任到 `codex-gpt-work`。
