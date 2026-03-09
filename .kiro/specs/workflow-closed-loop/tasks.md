# workflow-closed-loop — 任务清单

> **Authority**: `.kiro/specs/workflow-closed-loop/requirements.md` + design.md + `.kiro/specs/SPEC_TASKS_SCAN.md`

---

## Task 1：协议对象与目录

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 1.1 | 创建 `.kiro/runtime/` 下 findings / triage / assignments / deliveries / verdicts / merges / blockers 目录规范与索引文件规则 | 目录和索引规则在代码/文档中明确定义 | [x] |
| 1.2 | 为 finding / triage_decision / assignment / delivery / review_verdict / merge_decision / blocker 定义 JSON schema 或等价校验逻辑 | 每类对象都有稳定字段和 schema 测试 | [x] |
| 1.3 | 实现统一的对象读写辅助模块（ID、时间戳、状态迁移、索引维护） | 有单元测试覆盖 create/load/update/index | [x] |

## Task 2：audit 进入主协议

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 2.1 | 扩展 `workflow_audit_state.py`：区分运行状态与 finding 产出，不再只写 `audit-state/*.json` | audit-state 保留 heartbeat 语义，findings 独立落盘 | [x] |
| 2.2 | 新增 audit finding 写入路径：`audit-a` / `audit-b` 能创建 finding 对象并带 `finding_ref/spec/severity/summary` | 有单测证明 finding 可创建并被索引 | [x] |
| 2.3 | orchestrator 读取 open findings，并为 main 生成 triage 队列视图 | `workflow_snapshot.json` 能看到 pending findings | [x] |

## Task 3：review verdict 回流

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 3.1 | 为 `review` 定义结构化 `review_verdict` 对象（APPROVE / FIX_NEEDED / REJECT） | verdict 有 schema、owner、关联 delivery_id | [x] |
| 3.2 | review 执行完成后除文本结果外，必须写入 verdict 对象 | `executions/review/result.json` 不再是唯一事实来源 | [x] |
| 3.3 | review 在发现新问题时写入 finding 对象并关联对应 delivery/verdict | 可从 verdict 追到 new findings | [x] |

## Task 4：main triage 与 assignment

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 4.1 | main 读取 findings / verdicts / blockers，并生成 `triage_decision` | 不再只基于 git 状态决定 assign/review/monitor | [x] |
| 4.2 | main 根据 triage 生成结构化 assignment，对应 target agent/worktree/spec/task_refs | assignment 可供 coding 消费 | [x] |
| 4.3 | mailbox 引用具体 assignment/triage 对象 ID，而不是只给 summary 文本 | mailbox 中有 `object_type/object_id` 或等价字段 | [x] |
| 4.4 | main 在 assignment 前校验 `WORKTREE_ASSIGNMENTS.md` 的人工边界，不越权改派 | 冲突时生成 blocker，而非直接派单 | [x] |

## Task 5：coding delivery

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 5.1 | coding agent 消费 assignment，回写 claim / in_progress | 同一 assignment 不会被两个 coding agent 同时处理 | [x] |
| 5.2 | coding 完成后写入 delivery，对应 commit_refs、changed_files、tests_run、summary | review 可据此进入审校 | [x] |
| 5.3 | coding 阻塞时写 blocker，并把 assignment 状态推进到 blocked/returned | main 可读取并重新分配或等待 | [x] |

## Task 6：review 消费 delivery

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 6.1 | review mailbox 以 delivery 为输入，而不是只看 `ahead_of_main` | review dispatch 可看到具体 delivery_id | [x] |
| 6.2 | review 根据 delivery 产出 verdict，并把 delivery 状态推进到 reviewed | 状态链可追踪 | [x] |
| 6.3 | APPROVE 时生成 merge_decision；FIX_NEEDED/REJECT 时生成新 finding 或 returned assignment | main 能据此继续闭环 | [x] |

## Task 7：merge / reassign 收口

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 7.1 | main 消费 verdict，生成 merge_decision 或 reassign 决策 | `main` 可从 verdict 进入 merge/reassign | [x] |
| 7.2 | merge 后相关对象链条统一收口（assignment/delivery/verdict/finding 关联完成） | 任何 merged 对象都可从 index 追踪全链路 | [x] |
| 7.3 | reassign 时保留历史链路，不覆盖旧 assignment/delivery/verdict | 可查看完整回流历史 | [x] |

## Task 8：claim / lease / 幂等

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 8.1 | 为可消费对象实现 claim/lease 机制 | 崩溃恢复和重复消费有单测 | [x] |
| 8.2 | executor/orchestrator 重复运行时保持幂等 | 重跑不会重复推进状态 | [x] |
| 8.3 | heartbeat 中记录当前对象 ID 和 claim 状态 | snapshot 能展示谁在处理什么 | [x] |

## Task 9：汇总视图与观测

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 9.1 | 扩展 `workflow_snapshot.json`，汇总 findings/assignments/deliveries/verdicts/merges/blockers 计数与 active object | snapshot 可作为单一运行态总览 | [x] |
| 9.2 | 新增 `workflow_objects.md`、`workflow_blockers.md` 可读视图 | 人工无需逐目录 grep 才能理解现状 | [x] |
| 9.3 | terminal-control 改为根据结构化对象状态催办，而不是仅靠 mailbox summary | 表现层与协议事实一致 | [x] |

## Task 10：supervisor 与自动化链补齐

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 10.1 | `workflow_supervisor.py` 同时拉起 orchestrator、workflow_agent、workflow_executor | 自动化链完整运行 | [x] |
| 10.2 | supervisor/watch 能检查对象链是否卡死（如 pending too long / lease expired） | 有死锁/停滞检测 | [x] |
| 10.3 | 文档更新：WORKFLOW_CONTROL_GUIDE / scripts/README / 相关运行文档对齐完整闭环 | 文档与实现一致 | [x] |

## Task 11：测试与验收

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 11.1 | 单元测试：schema、状态迁移、owner、claim、幂等 | `pytest` 通过 | [x] |
| 11.2 | 集成测试：`audit -> main -> coding -> review -> main -> merge/reassign` 全链路 | 存在可执行场景 | [x] |
| 11.3 | 故障恢复测试：agent 重启、重复执行、过期 lease、blocked 回流 | 闭环可恢复 | [x] |

---

## 执行顺序

1. Task 1：先建立对象模型和基础读写
2. Task 2-4：先打通 `audit/review -> main -> assignment`
3. Task 5-7：再打通 `coding -> review -> main -> merge/reassign`
4. Task 8-10：补幂等、观测、supervisor
5. Task 11：补全自动化验收

---

## 收口标准

- [x] 6 个窗口全部进入同一套文件协议主链
- [x] `audit/review` 的新发现能稳定回流给 `main`
- [x] `main` 的分配可被 `coding` 稳定消费并回写 delivery
- [x] `review` 的 verdict 能驱动 merge 或重新分配
- [x] 任一 agent 中断后闭环可恢复
