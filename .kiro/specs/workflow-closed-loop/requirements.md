# workflow-closed-loop — 多 Agent 文件协议闭环

> **目标**: 将 `audit-a` / `audit-b` / `review` / `main` / `codex` / `codex-gpt` 串成可恢复、可审计、可分配的完整文件协议闭环
> **优先级**: P0
> **预估工作量**: 3-5 天

---

## 1. 背景与动机

### 1.1 当前问题

现有 workflow automation 已具备以下局部能力：

- `workflow_orchestrator.py` 可生成 `mailboxes/*.json`
- `workflow_executor.py` 可读取 mailbox 并调用对应 CLI
- `workflow_terminal_control.py` 可对已打开窗口发送固定话术
- `audit-a` / `audit-b` 可通过 `audit-state/*.json` 维持运行状态

但这套机制仍不是完整闭环，存在结构性缺口：

- `audit-a` / `audit-b` 未进入主协议，只是终端控制器的旁路输入
- `review` 没有结构化 verdict / findings 输出，无法驱动下一轮统筹分配
- `main` 的统筹决策主要基于 git worktree 状态，不能消费审计/审校新发现
- `coding -> review -> main -> coding` 的任务回流依赖自然语言结果与人工理解，不可自动恢复
- 文件协议中缺少 `finding`、`assignment`、`delivery`、`review_verdict` 等一等对象

### 1.2 设计目标

- 让 6 个窗口全部进入同一套文件协议，而不是旁路驱动
- 让 `audit/review` 的新需求成为 `main` 可消费的结构化输入
- 让 `main` 的分配成为 `coding` 可消费的结构化任务，而不是仅靠 git 状态猜测
- 让任何一个 agent/窗口中断后，系统仍能通过 runtime 文件恢复执行
- 让 `SPEC_TASKS_SCAN`、`.kiro/WORKTREE_ASSIGNMENTS.md` 与 runtime 协议保持一致

---

## 2. 用户故事

### 2.1 作为统筹者（main）

**故事 1：读取新发现并重新分配**

作为统筹者  
我希望从结构化 findings / review verdict 文件中读取新需求  
这样我可以把任务可靠地分配给 `codex` / `codex-gpt`

**验收标准**：

- [ ] `main` 不仅能读取 git/worktree 状态，也能读取 `audit` / `review` 产出的结构化对象
- [ ] 新 findings 经过 triage 后会生成 assignment 文件，而不是只停留在文本结果里
- [ ] assignment 明确包含 owner、目标 worktree、相关 spec、优先级、依赖和验收要求

### 2.2 作为编码者（codex / codex-gpt）

**故事 2：基于 assignment 接单并交付**

作为编码者  
我希望消费结构化 assignment  
这样我可以明确自己当前应该做什么、做到什么程度、完成后回写什么

**验收标准**：

- [ ] coding agent 读取 assignment 而非仅靠 `wait_for_assignment` 文本判断
- [ ] coding 交付后生成结构化 delivery 记录，包含 commit、task refs、阻塞与结果
- [ ] review 能基于 delivery 记录而不是只靠 git log 进入审校

### 2.3 作为审校者（review）

**故事 3：审校后产出可回流 verdict**

作为审校者  
我希望对 delivery 产出结构化 verdict 和新 findings  
这样 main 能继续统筹下一轮，而不是人工阅读自然语言输出

**验收标准**：

- [ ] review 产出 `APPROVE / FIX_NEEDED / REJECT` 的结构化 verdict 文件
- [ ] 若审校中发现新问题，必须生成新的 finding 对象并与相关 delivery 关联
- [ ] main 可直接消费 review verdict 决定 merge、退回或再分配

### 2.4 作为审计者（audit-a / audit-b）

**故事 4：持续审计并进入主闭环**

作为审计者  
我希望我的发现进入主协议  
这样发现不会停留在旁路状态，而会被统筹消费并最终落到编码/审校闭环

**验收标准**：

- [ ] audit 不再只写 `audit-state/*.json`，还会产出结构化 findings
- [ ] audit findings 能被 main triage 并生成 assignment
- [ ] audit findings 的生命周期可追踪到 delivered / reviewed / merged / deferred

---

## 3. 功能需求

### 3.1 FR-1：统一的工作流对象模型

系统必须定义并落地以下一等对象：

- `finding`
- `triage_decision`
- `assignment`
- `delivery`
- `review_verdict`
- `merge_decision`
- `blocker`

**验收标准**：

- [ ] 每类对象都有独立 JSON schema 或等价结构约束
- [ ] 每类对象有唯一 ID、状态、owner、created_at、updated_at
- [ ] 对象之间存在明确关联字段（如 `finding_id`、`assignment_id`、`delivery_id`）

### 3.2 FR-2：完整状态机

系统必须显式定义从发现到合并的状态迁移：

`new -> triaged -> assigned -> in_progress -> delivered -> reviewed -> merged`

以及异常支线：

`blocked`
`rejected`
`deferred`
`superseded`

**验收标准**：

- [ ] 每种状态迁移都有唯一 owner
- [ ] 非 owner 不得擅自推进状态
- [ ] 非法迁移会被拒绝并记录错误

### 3.3 FR-3：audit 进入主协议

`audit-a` / `audit-b` 必须成为主协议参与者，而不是仅靠 `audit-state` 存活。

**验收标准**：

- [ ] audit findings 被写入主 runtime 协议目录
- [ ] `audit-state` 仅作为运行心跳/状态补充，不再承担 finding 载体职责
- [ ] orchestrator 会读取 audit findings 并作 triage

### 3.4 FR-4：review verdict 回流

review 的输出必须结构化并可供 main 读取。

**验收标准**：

- [ ] review 的 verdict 文件包含 `verdict`、`summary`、`finding_ids`、`delivery_id`、`next_action`
- [ ] review 失败或发现新问题时，会产出结构化 findings / blockers
- [ ] main 能根据 verdict 自动决定 merge、退回或重新分配

### 3.5 FR-5：assignment 驱动 coding

coding agent 必须由 assignment 驱动，而不是只由“窗口催办”驱动。

**验收标准**：

- [ ] mailbox 能引用当前 assignment，而不是只有笼统 summary
- [ ] `codex` / `codex-gpt` 可识别 assignment 的 owner、spec、依赖、完成定义
- [ ] coding 完成后回写 delivery，并推动 review 队列

### 3.6 FR-6：与 spec 真源一致

runtime 闭环必须与 `SPEC_TASKS_SCAN` / `WORKTREE_ASSIGNMENTS.md` 对齐。

**验收标准**：

- [ ] assignment 会引用 spec 名称、task 编号或 finding 编号
- [ ] triage/assignment 不允许脱离 spec 真源漂移
- [ ] 如需新增 spec 或 backlog，必须能通过协议对象反映给 main

### 3.7 FR-7：恢复与幂等

系统必须支持 agent 重启、窗口关闭、重复执行后的恢复。

**验收标准**：

- [ ] 同一 assignment / verdict / finding 重复消费不会产生重复状态推进
- [ ] 每类对象支持 owner claim 或等价机制
- [ ] 任一 agent 重启后可从 runtime 文件恢复当前上下文

### 3.8 FR-8：可观察与审计

协议流必须可调试、可审计、可追责。

**验收标准**：

- [ ] runtime 中存在对象索引或状态汇总文件
- [ ] 能从 finding 追到 assignment、delivery、review_verdict、merge_decision
- [ ] 每次状态变化有时间戳、actor、reason

---

## 4. 非功能需求

### 4.1 NFR-1：文件协议优先

- 使用仓库内文件作为共享协调介质
- 不引入数据库或外部消息队列作为第一阶段前置依赖

**验收标准**：

- [ ] 所有闭环核心对象都在 `.kiro/runtime/` 下持久化
- [ ] 单机环境下重启后协议状态仍可恢复

### 4.2 NFR-2：可迁移性

- 文件协议未来可迁移到 DB / queue / event bus
- 当前 schema 不得绑定 PowerShell 或特定 CLI 文本格式

**验收标准**：

- [ ] JSON 结构不依赖终端窗口实现细节
- [ ] owner / state / relation 字段具备稳定语义

### 4.3 NFR-3：安全与隔离

- 不允许任意 agent 修改非自己 owner 的状态对象
- review / main 的决策对象需要更高权限边界

**验收标准**：

- [ ] 状态变更有 owner 校验
- [ ] 非法写入有错误记录

---

## 5. 验收标准总览

### 5.1 功能验收

- [ ] audit findings 能进入 main 的 triage 队列
- [ ] main 能从 triage 生成 assignment 分配到 coding
- [ ] coding 完成后生成 delivery 并触发 review
- [ ] review 产出 verdict 与新 findings，重新回流给 main
- [ ] merge 决策与主线状态可从协议对象追踪

### 5.2 韧性验收

- [ ] 任一 agent 停止后重启可恢复未完成对象
- [ ] 重复运行 orchestrator / executor 不会重复推进同一状态
- [ ] 控制器停掉后，协议主链仍可工作

### 5.3 一致性验收

- [ ] protocol 对象与 `SPEC_TASKS_SCAN` / spec tasks 一致
- [ ] runtime 不会生成无 spec 归属的 assignment
- [ ] `WORKTREE_ASSIGNMENTS.md` 仍保持人工分配 authority，不被协议越权覆盖

---

## 6. 约束与假设

### 6.1 约束

- 当前采用 Git Worktree 多目录协作模式
- `WORKTREE_ASSIGNMENTS.md` 仍是人工分配唯一真源
- 协议必须兼容现有 `mailboxes/acks/heartbeats/executor-state` 目录

### 6.2 假设

- 当前部署环境以单机本地开发/审校为主
- 可接受在 `.kiro/runtime/` 下增加多个子目录和索引文件

---

## 7. 风险与缓解

### 7.1 风险：状态对象过多导致认知负担上升

**缓解**：

- 设计统一 schema 和状态索引
- 用汇总视图代替人工逐目录查看

### 7.2 风险：协议与人工 authority 冲突

**缓解**：

- 明确 `WORKTREE_ASSIGNMENTS.md` 负责“人工分配边界”
- runtime 协议只在该边界内推进对象状态，不越权改派 worktree

### 7.3 风险：历史兼容破坏现有脚本

**缓解**：

- 保留现有 mailbox/ack 路径
- 增量引入 findings/assignments/deliveries/verdicts

---

## 8. Definition of Done

### 8.1 协议对象

- [ ] finding / assignment / delivery / review_verdict / merge_decision / blocker 已定义
- [ ] 每种对象具备 schema、owner、状态迁移

### 8.2 主闭环

- [ ] `audit -> main`
- [ ] `review -> main`
- [ ] `main -> coding`
- [ ] `coding -> review`
- [ ] `review -> main`
- [ ] `main -> merge / reassign`

### 8.3 恢复与观测

- [ ] 重启恢复可验证
- [ ] 索引视图可追踪对象全链路
- [ ] 关键脚本存在单元测试

---

## 9. 参考文档

- `docs/WORKTREE_GUIDE.md`
- `.kiro/WORKTREE_ASSIGNMENTS.md`
- `.kiro/specs/SPEC_TASKS_SCAN.md`
- `scripts/README.md`

---

**维护者**: main worktree / orchestrator
**最后更新**: 2026-03-07
