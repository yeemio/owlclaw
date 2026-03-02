# Console 审校报告（2026-03-02）

## 范围
- 分支：`codex-work`（console-backend-api Task 0-10）
- 分支：`codex-gpt-work`（console-frontend Task 0-7）
- 基线：`main`（commit `10efeb4`）

## 审校结论
- `codex-work`：`FIX_NEEDED`
- `codex-gpt-work`：`FIX_NEEDED`

## 关键问题（阻塞合并）

### 1) 前后端 API 契约不一致（高）
- 前端请求 `/governance?granularity=...`，后端仅提供 `/governance/budget`、`/governance/circuit-breakers`、`/governance/visibility-matrix`。
- 前端 Ledger query 参数名使用 `agent/capability/start_time/end_time`，后端实际为 `agent_id/capability_name/start_date/end_date`。
- 前端将 Ledger 列表解析为 `{ records, total, limit, offset }`，后端返回 `{ items, total, offset, limit }`。
- 前端 Agents/Capabilities/Triggers 解析与后端返回结构不一致（前端按数组或 `capabilities/triggers` 读取；后端统一 `{ items: [...] }`）。

影响：页面数据为空、请求 404/422、筛选失效。

### 2) 后端错误响应结构未统一（中）
- 多处 404 通过 `HTTPException(detail=...)` 返回 `{"detail": ...}`，未统一到 Task 1.4 要求的 `ErrorResponse`（`{"error": {...}}`）。
- 现有测试多仅断言 status code，未锁定错误响应结构，回归风险未覆盖。

## 验证记录
- 后端：`poetry run pytest tests/unit/web tests/integration/test_console_api.py -q` 通过（41 passed）。
- 前端已提交快照（`codex-gpt-work@1cfb418`）隔离验证：`npm ci && npm run build` 通过。

## 修复分配建议（供统筹）
- `codex-work`：
  - 统一 API 4xx/5xx 错误模型为 `ErrorResponse`（含 404）。
  - 增补单测：断言错误响应 JSON 结构，不仅断言状态码。
- `codex-gpt-work`：
  - 重做 `src/hooks/useApi.ts` 为“后端契约映射层”，统一路径/参数/字段映射。
  - 页面层仅消费 ViewModel，不直接耦合后端字段。
  - 补最小契约测试覆盖 governance/ledger/agents/capabilities/triggers。

## 审校人
- worktree: `D:\AI\owlclaw-review`
- branch: `review-work`
