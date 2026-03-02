# Console Backend 修复收口报告（codex-work）

## 范围
- worktree: `D:\AI\owlclaw-codex`
- branch: `codex-work`
- spec: `console-backend-api`（审校修复闭环）

## 已完成修复
1. 统一 4xx/5xx 错误响应为 `ErrorResponse`（`{"error": {...}}`），覆盖 `HTTPException` 与 `RequestValidationError`。
2. 固定后端真实契约文档：`docs/CONSOLE_BACKEND_CONTRACT.md`（REST + WS + ErrorResponse）。
3. 补契约一致性测试：Governance/Ledger/WS 消息类型。
4. 回写 spec 规范化：
   - `console-backend-api` requirements/design/tasks 与实现状态一致（无未勾选残留）。
   - `SPEC_TASKS_SCAN` checkpoint 更新为事实状态并附验证证据。
5. 修复 `capabilities` provider 类型问题并补单测分支覆盖。

## 关键提交（backend 修复链）
- `d68bacd` fix(web): align console backend error and contract coverage
- `e0946c8` chore(governance): normalize spec scan checkpoint and error envelope coverage
- `6b36fd4` docs(governance): normalize console-backend-api spec contract details
- `26600b8` docs(governance): mark console-backend-api requirements and design complete
- `6685966` fix(governance): tighten capabilities provider typing and coverage
- `640d7b9` chore(governance): refresh checkpoint with backend quality gate evidence

## 验证记录
- `poetry run mypy owlclaw/web` -> passed（24 files, no issues）
- `poetry run ruff check owlclaw/web/contracts.py owlclaw/web/api owlclaw/web/providers tests/unit/web tests/integration/test_console_api.py` -> passed
- `poetry run pytest tests/unit/web tests/integration/test_console_api.py` -> 51 passed
- `poetry run pytest tests/unit/web tests/integration/test_console_api.py --cov=owlclaw/web --cov-report=term` -> 51 passed, total coverage 82%

## 当前状态
- `codex-work` 工作区 clean（零残留）。
- backend 分配项已完成，等待 `review-work` 复审与合并。
