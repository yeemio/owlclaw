# 增量审校报告（2026-03-02 Round 11）

## 范围
- `codex-work` / `codex-gpt-work` 当前头：`c14006b`（Merge branch 'codex-gpt-work'）
- 重点对照：`9e504a4`（fix(agent): complete audit-fix-high H1 H4 and docs sync）

## 审校结论
- `FIX_NEEDED`

## Findings（按严重度）

### P0: H1 修复被合并回退（代码与测试同时回退）
`c14006b` 相对 `9e504a4` 将 Heartbeat 的 schedule 事件源实现回退为 MVP 占位。

证据（`git diff 9e504a4..c14006b -- owlclaw/agent/runtime/heartbeat.py tests/unit/agent/test_heartbeat.py`）：
- `heartbeat.py` 回退点：
  - 删除 `schedule_client`、`_list_scheduled_tasks()`、`_schedule_task_is_due()`、`_coerce_datetime()`
  - `_check_schedule_events()` 恢复为 “MVP: returns False”
  - `database_pending_statuses` 默认从 `("error","timeout","pending")` 回退到 `("pending","queued")`
- `test_heartbeat.py` 回退点：
  - 删除 schedule 事件源相关测试用例（due/future/window/missing timestamp）
  - 删除 extension source warning 覆盖

影响：`audit-fix-high` Task 0（H1）在代码层不成立，但任务勾选与 scan 仍显示完成，属于阻断级事实不一致。

### P1: H4 前端治理映射被回退
`c14006b` 相对 `9e504a4` 回退了 Governance 的兼容映射逻辑。

证据（`git diff 9e504a4..c14006b -- owlclaw/web/frontend/src/hooks/useApi.ts`）：
- 删除 `capability_name -> name` 映射（CircuitBreaker）
- 删除 visibility 扁平项（`agent_id/capability_name/visible`）分组逻辑
- 保留了 budget `period_start/total_cost` 映射（该部分未回退）

影响：后端返回兼容形态时，前端治理页数据将退化或丢失，`audit-fix-high` Task 3（H4）不能宣告完成。

### P1: 编码分支零残留规则违反（流程风险）
`codex-gpt-work` 当前存在未提交修改（working tree 脏），与分配文件“零残留规则”冲突。

证据：`git -C D:\ai\owlclaw-codex-gpt status --short` 显示多文件 `M`。

## 验证记录
- 针对 `9e504a4` 的单点验证（历史提交层面）是通过的：
  - `poetry run pytest tests/unit/agent/test_heartbeat.py -q` → `18 passed`
  - `npm run test -- --run src/__tests__/useApi.contract.test.tsx` → `2 passed`
- 但当前头 `c14006b` 已将上述修复/测试覆盖回退，形成回归。

## 建议
1. 以 `9e504a4` 为基线重新应用 H1/H4 代码与测试，避免 merge 回退。
2. 将 `audit-fix-high` 的 Task 0/3 勾选状态暂时回滚为未完成，待代码恢复并验证后再勾选。
3. 清理 `codex-gpt-work` 未提交修改，恢复零残留，再进入下一轮审校。
