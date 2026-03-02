# Console 复审报告（2026-03-02 Round 8）

## 范围
- 目标提交：
  - `codex-work@6685966`（fix(governance): tighten capabilities provider typing and coverage）
  - `codex-gpt-work@79f0721`（test(skills): close openclaw tutorial and compatibility acceptance tasks）
- 对照基线：Round 7 结论（`review-work@e900b95`）

## 审校结论
- `codex-work`: `FIX_NEEDED`（既有 console 阻断仍在；但覆盖率问题已修复）
- `codex-gpt-work`: `FIX_NEEDED`（既有 console 残留契约问题仍在；本次 skills 提交本身通过）

## Findings（按严重度）

### P0（延续）: `codex-work` 前端消费契约阻断仍未修复
本轮 `6685966` 仅修改 capabilities provider 与其单测，未触及前端 hooks/pages 的 envelope 消费逻辑。

影响：Round 6/7 记录的运行时风险（页面数组根对象假设）仍未解除，分支仍不可批准合并。

### P1（延续）: `codex-gpt-work` 两处 console 契约残留仍在
`79f0721` 为 skills 侧测试/文档勾选，不涉及 console hooks；Round 7 两个问题仍存在：
- `useWebSocket.ts` overview 仍读取 `payload.data`，后端为 `payload.payload`
- `useApi.ts` governance budget 仍按 `date/cost` 读，后端行字段为 `period_start/total_cost`

证据（当前 HEAD）：
- `owlclaw/web/frontend/src/hooks/useWebSocket.ts:43`
- `owlclaw/web/frontend/src/hooks/useApi.ts:200-201,462`

## Positive Changes（本轮确认）
- Round 6 的“覆盖率 >80% 勾选不实”问题已被 `6685966` + 新增测试修复：
  - 命令：`poetry run pytest tests/unit/web tests/integration/test_console_api.py --cov=owlclaw.web --cov-fail-under=80 -q`
  - 结果：`51 passed`，`owlclaw.web TOTAL 82.16%`（门槛达成）
- `79f0721` 新增/勾选项具备自动化证据：
  - `poetry run pytest tests/unit/test_openclaw_tutorial_constraints.py -q` → `3 passed`
  - `poetry run pytest tests/integration/test_openclaw_skill_compatibility.py -q` → `3 passed`

## 建议
1. `codex-gpt-work` 优先收口 Round 7 两个 console 残留契约点（WS payload 字段 + budget 字段映射）。
2. `codex-work` 若继续保留前端改动责任，需同步完成前端 envelope 消费修复；否则由统筹回收职责到 `codex-gpt-work`。
3. 覆盖率问题已解除，可从阻断清单移除该项。
