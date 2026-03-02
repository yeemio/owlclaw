# Console 复审报告（2026-03-02 Round 6）

## 范围
- 目标提交：
  - `codex-work@6b36fd4`（docs(governance): normalize console-backend-api spec contract details）
  - `codex-work@26600b8`（docs(governance): mark console-backend-api requirements and design complete）
- 对照基线：`review-work@c76d7a0`

## 审校结论
- `codex-work`: `FIX_NEEDED`
- `codex-gpt-work`: 本轮无新提交（保持上轮 `FIX_NEEDED`）

## Findings（按严重度）

### P0: 既有前端契约阻断未修复，但文档已宣告完成
本轮新增提交仅修改 spec 文档，未触及前端消费契约代码；Round5 的阻断问题仍然存在。

证据（仍在当前 `codex-work` HEAD）：
- `owlclaw/web/frontend/src/hooks/useApi.ts:28` — `useAgents` 仍按数组根对象声明
- `owlclaw/web/frontend/src/hooks/useApi.ts:32` — `useCapabilities` 仍按数组根对象声明
- `owlclaw/web/frontend/src/hooks/useApi.ts:36` — `useTriggers` 仍按数组根对象声明
- `owlclaw/web/frontend/src/pages/Agents.tsx:8` — `(data ?? []).map(...)`
- `owlclaw/web/frontend/src/pages/Capabilities.tsx:23` — `(data ?? []).map(...)`
- `owlclaw/web/frontend/src/pages/Triggers.tsx:13` — `(data ?? []).map(...)`
- 后端真实 envelope：
  - `owlclaw/web/api/agents.py:24` `return {"items": items}`
  - `owlclaw/web/api/capabilities.py:27` `return {"items": items}`
  - `owlclaw/web/api/triggers.py:28` `return {"items": items}`

影响：运行时 `map is not a function` 风险未解除，分支仍不可批准合并。

### P1: requirements 勾选“覆盖率 >80%”与实测不符（文档超前宣告）
`26600b8` 将 `requirements.md` 的“单元测试覆盖率 > 80%”勾选为完成，但针对 console 后端模块的覆盖率实测未达到 80%。

实测命令：
- `poetry run pytest tests/unit/web tests/integration/test_console_api.py --cov=owlclaw.web --cov-report=term --cov-fail-under=80 -q`

实测结果：
- `45 passed`
- `Coverage failure: total of 77 is less than fail-under=80`
- `TOTAL 77.28%`

影响：spec 完成态与验证事实不一致，会误导统筹排期与验收判断。

### P1: 分支职责越界状态未回收（流程风险）
本轮虽为 docs 提交，但 `codex-work` 分支仍承载前端路径改动（历史提交 `a91dbca`），与当前分配规则冲突，需统筹确认是否变更分工。

证据：
- 规则：`.kiro/WORKTREE_ASSIGNMENTS.md` 中 `codex-work` 禁止触碰 `owlclaw/web/frontend/**`、`owlclaw/web/static/**`
- 现状：`codex-work` 历史提交已改动上述路径，且阻断问题仍滞留在该分支。

## 建议
1. 先修复 `codex-work` 前端消费 envelope 的 P0 问题，再谈 spec 完成标记。
2. 将 `requirements.md` 中覆盖率勾选回退为未完成，或补齐测试使 `owlclaw.web >= 80%` 后再勾选。
3. 统筹确认并明确前端改动归属（是否允许 `codex-work` 继续处理前端）。
