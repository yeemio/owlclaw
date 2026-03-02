# Console 复审报告（2026-03-02 Round 4）

## 范围
- 目标提交：`codex-work@a91dbca`（feat(web): complete console frontend and integration）
- 对照基线：`main@8cb09a8`

## 审校结论
- `codex-work`: `FIX_NEEDED`
- `codex-gpt-work`: 本轮无新提交可复审（保持上轮结论）

## Findings（按严重度）

### P0: 前端运行时契约不一致，页面将出现 `map is not a function`
后端 `/agents`、`/capabilities`、`/triggers` 返回结构均为 `{"items": [...]}`，但前端 hooks 仍按“数组根对象”解析，页面层直接 `(data ?? []).map(...)`。

证据：
- 前端 hooks 返回数组（错误假设）：
  - `useAgents()` -> `apiFetch<Array<...>>("/agents")`
  - `useCapabilities()` -> `apiFetch<Array<...>>("/capabilities")`
  - `useTriggers()` -> `apiFetch<Array<...>>("/triggers")`
  - 文件：`owlclaw/web/frontend/src/hooks/useApi.ts`（27-37 行）
- 页面直接按数组 map：
  - `Agents.tsx` 第 8 行 `(data ?? []).map(...)`
  - `Capabilities.tsx` 第 23 行 `(data ?? []).map(...)`
  - `Triggers.tsx` 第 13 行 `(data ?? []).map(...)`
- 后端真实返回：
  - `owlclaw/web/api/agents.py` 第 24 行 `return {"items": items}`
  - `owlclaw/web/api/capabilities.py` 第 27 行 `return {"items": items}`
  - `owlclaw/web/api/triggers.py` 第 28 行 `return {"items": items}`

影响：进入对应页面会在运行时抛错或渲染空白，属于阻断级问题。

### P1: 后端错误响应结构仍未统一到 ErrorResponse
多个 404 仍使用 `HTTPException(detail=...)`，返回 `{"detail": ...}`，与 Task 1.4 的统一 `ErrorResponse` 约束不一致。

证据：
- `owlclaw/web/api/ledger.py` 第 72 行
- `owlclaw/web/api/agents.py` 第 36 行
- `owlclaw/web/api/capabilities.py` 第 38 行

### P1: 分支职责越界（流程风险）
当前分配文档明确 `codex-work` 禁止触碰 `owlclaw/web/frontend/**` 与 `owlclaw/web/static/**`，但 `a91dbca` 大量改动了上述路径。

证据：
- 分配规则：`.kiro/WORKTREE_ASSIGNMENTS.md`（"禁止触碰" 条目）
- 提交范围：`git show --name-status a91dbca` 包含前端与静态产物。

## 验证记录
- 后端测试（通过）：
  - `poetry run pytest tests/unit/web tests/integration/test_console_api.py tests/integration/test_console_integration.py tests/integration/test_console_mount.py tests/unit/cli/test_console_cmd.py tests/unit/test_app_console_mount.py -q`
  - 结果：`50 passed`
- 前端构建与测试（通过）：
  - `npm run build`
  - `npm run test -- --run`
  - 说明：当前测试未覆盖前后端真实响应 envelope 对齐，未能捕获 P0 运行时契约问题。

## 建议
1. 先修 `useApi.ts`：统一把 `/agents|/capabilities|/triggers` 解析为 `response.items`，并在 hook 层输出页面可直接消费的数组。
2. 增加最小契约测试：模拟后端真实 `{"items": [...]}` 响应，覆盖 Agents/Capabilities/Triggers 页面渲染。
3. 后端统一 404/4xx 为 `ErrorResponse` 并补断言结构测试。
4. 统筹层执行职责边界回收：前端后续改动回到 `codex-gpt-work`，避免再次越界。
