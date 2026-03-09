# workflow-closed-loop — 设计文档

> **对应需求**: `.kiro/specs/workflow-closed-loop/requirements.md`

---

## 1. 设计原则

### D1：采用共享黑板式文件协议

以 `.kiro/runtime/` 作为共享协调介质，所有角色通过结构化文件对象交互，而不是直接依赖窗口文本。

运行机制采用三层：

- **对象层**：`findings` / `triage` / `assignments` / `deliveries` / `verdicts` / `merges` / `blockers`
- **投递层**：现有 `mailboxes` / `acks` / `heartbeats`
- **展示层**：`dispatch/*.md`、terminal-control 固定话术、human-readable 汇总

### D2：保留现有 mailbox/ack 作为执行控制层

`mailbox` 不再承担全部业务语义，只负责告诉某个 agent：

- 当前应处理哪个对象
- 当前阶段是什么
- 处理成功后应回写哪个对象

对象事实本身存于独立目录，不再仅存在于 summary 文本。

### D3：人工 authority 与 runtime protocol 分离

- `.kiro/WORKTREE_ASSIGNMENTS.md`：人工定义 worktree 分工边界
- `.kiro/specs/SPEC_TASKS_SCAN.md`：spec 真源与任务 authority
- `.kiro/runtime/`：运行态对象、状态推进、恢复与调度

runtime 不得越权修改人工分工文件，但必须引用其结论。

---

## 2. 目录结构

新增以下 runtime 目录：

```text
.kiro/runtime/
├── findings/
│   ├── open/
│   ├── triaged/
│   ├── assigned/
│   ├── closed/
│   └── index.json
├── triage/
│   ├── pending/
│   ├── completed/
│   └── index.json
├── assignments/
│   ├── pending/
│   ├── active/
│   ├── delivered/
│   ├── reviewed/
│   └── index.json
├── deliveries/
│   ├── pending_review/
│   ├── reviewed/
│   └── index.json
├── verdicts/
│   ├── pending_main/
│   ├── applied/
│   └── index.json
├── merges/
│   ├── pending/
│   ├── completed/
│   └── index.json
├── blockers/
│   ├── open/
│   ├── resolved/
│   └── index.json
├── mailboxes/
├── acks/
├── heartbeats/
├── dispatch/
├── executor-state/
└── workflow_snapshot.json
```

---

## 3. 对象模型

### 3.1 finding

用途：`audit-a`、`audit-b`、`review` 产出新问题/新需求。

```json
{
  "schema_version": 1,
  "id": "finding-20260307-001",
  "source": "audit-a",
  "source_type": "audit",
  "status": "new",
  "title": "Runtime tool sanitization gap",
  "summary": "Observation tool exposes unsanitized args",
  "severity": "p1",
  "refs": {
    "spec": "audit-deep-remediation",
    "task": "D48",
    "files": ["owlclaw/agent/runtime/runtime.py"]
  },
  "relations": {
    "parent_delivery_id": "",
    "parent_verdict_id": ""
  },
  "owner": "main",
  "created_at": "...",
  "updated_at": "...",
  "history": []
}
```

### 3.2 triage_decision

用途：`main` 对 finding 的处理结论。

状态：

- `pending`
- `accepted`
- `deferred`
- `rejected`
- `split`

关键字段：

- `finding_ids`
- `decision`
- `assigned_spec`
- `target_worktree`
- `reason`

### 3.3 assignment

用途：`main` 给 coding worktree 的正式分配对象。

状态：

- `pending`
- `claimed`
- `in_progress`
- `delivered`
- `returned`
- `cancelled`

关键字段：

- `target_agent`
- `target_branch`
- `spec`
- `task_refs`
- `finding_ids`
- `depends_on`
- `acceptance`

### 3.4 delivery

用途：`codex` / `codex-gpt` 回写交付结果。

状态：

- `pending_review`
- `reviewing`
- `approved`
- `fix_needed`
- `rejected`

关键字段：

- `assignment_id`
- `branch`
- `commit_refs`
- `changed_files`
- `tests_run`
- `summary`
- `blockers`

### 3.5 review_verdict

用途：`review` 对 delivery 的结构化结论。

状态：

- `pending_main`
- `applied`

关键字段：

- `delivery_id`
- `verdict`
- `new_finding_ids`
- `merge_ready`
- `notes`

`verdict` 取值：

- `APPROVE`
- `FIX_NEEDED`
- `REJECT`

### 3.6 merge_decision

用途：`main` 根据 verdict 决定 merge / 回退 / 再分配。

状态：

- `pending`
- `merged`
- `reassigned`
- `blocked`

---

## 4. 状态机

### 4.1 audit / review 发现流

```text
audit-a|audit-b|review
  -> finding:new
  -> triage:pending
  -> triage:accepted|deferred|rejected|split
```

owner：

- finding 创建者：`audit-a` / `audit-b` / `review`
- triage owner：`main`

### 4.2 分配与编码流

```text
triage:accepted
  -> assignment:pending
  -> assignment:claimed
  -> assignment:in_progress
  -> delivery:pending_review
  -> assignment:delivered
```

owner：

- assignment 创建/推进：`main`
- claim / in_progress / delivery 写入：`codex` 或 `codex-gpt`

### 4.3 审校回流

```text
delivery:pending_review
  -> review_verdict:APPROVE|FIX_NEEDED|REJECT
  -> if APPROVE: merge_decision:pending
  -> if FIX_NEEDED/REJECT: finding:new or assignment:returned
```

owner：

- verdict：`review`
- merge / reassign：`main`

### 4.4 合并收口

```text
merge_decision:pending
  -> merged
  -> finding/assignment/delivery/verdict all linked as completed
```

---

## 5. 与现有脚本的职责映射

### 5.1 workflow_orchestrator.py

新增职责：

- 读取 open findings / pending triage / pending verdicts / open blockers
- 根据人工 authority 和当前 worktree 边界生成 assignment
- 将 mailbox 指向具体 assignment / verdict / triage 对象
- 更新 `workflow_snapshot.json`，加入对象统计与当前闭环阶段

不再仅根据 `ahead_of_main` 决定下一步。

### 5.2 workflow_agent.py

新增职责：

- 生成 dispatch 时引用具体对象 ID
- heartbeat 附带当前处理对象 ID
- 对 mailbox 变化不仅写 `ack seen`，还写当前 claim / phase

### 5.3 workflow_executor.py

新增职责：

- main：执行 triage / assignment / merge decision
- coding：执行 assignment 并回写 delivery
- review：消费 delivery 并回写 verdict

执行结果不能只落为自然语言文本，应同时落结构化对象。

### 5.4 workflow_terminal_control.py

角色保持展示/催办层，不承担协议事实真源职责。

控制器只根据协议对象和 mailbox 状态催办，不直接决定业务流向。

### 5.5 workflow_supervisor.py

必须同时拉起：

- `workflow_orchestrator.py`
- `workflow_agent.py` for each mailbox participant
- `workflow_executor.py` for each mailbox participant

否则协议链不完整。

---

## 6. owner / claim 规则

### 6.1 owner

| 对象 | owner |
|------|-------|
| finding | 创建它的 `audit-a` / `audit-b` / `review` |
| triage_decision | `main` |
| assignment | `main` |
| delivery | `codex` / `codex-gpt` |
| review_verdict | `review` |
| merge_decision | `main` |
| blocker | 发现阻塞的一方，解除由对应 owner 或 `main` |

### 6.2 claim

所有可被消费的对象都带 `claim`：

```json
{
  "claimed_by": "codex",
  "claimed_at": "...",
  "lease_seconds": 1800
}
```

用于防止重复消费和支持崩溃恢复。

---

## 7. 与 spec 真源的一致性

### 7.1 finding / assignment 必须引用 spec authority

finding 或 assignment 至少满足其一：

- `spec + task_ref`
- `spec + finding_ref`
- `spec = new-spec-needed`

若为 `new-spec-needed`，main 必须先补 spec，再生成正式 assignment。

### 7.2 与 `WORKTREE_ASSIGNMENTS.md` 的边界

main 在生成 assignment 时必须检查：

- target worktree 是否在人工允许边界内
- 是否违反独占路径约束
- 是否与当前人工分配冲突

若冲突，则生成 blocker，不直接改派。

---

## 8. 汇总视图

新增以下汇总文件：

- `workflow_snapshot.json`
  - 对象统计
  - 当前阶段
  - 每个 agent 的 active object
- `workflow_objects.md`
  - open findings
  - pending assignments
  - pending reviews
  - pending merges
- `workflow_blockers.md`
  - 当前所有 open blockers

---

## 9. 验证策略

### 9.1 单元测试

- schema 校验
- 状态迁移合法/非法路径
- owner/claim 校验
- orchestrator 根据 findings/verdicts 生成 assignment
- coding 回写 delivery
- review 回写 verdict

### 9.2 集成测试

- `audit -> main -> assignment`
- `assignment -> coding -> delivery -> review -> verdict -> main`
- 中途进程退出后恢复
- 重复消费幂等

### 9.3 回归测试

- 保证现有 `mailboxes/acks/heartbeats` 不被破坏
- terminal-control 仍能工作，但仅作为表现层

---

## 10. 实施顺序

### Phase A：协议与 schema

- 定义对象目录、schema、索引、状态迁移辅助函数

### Phase B：audit/review 回流

- audit findings 接主协议
- review verdict 与新 findings 接主协议

### Phase C：main 分配与 coding 交付

- assignment / delivery 正式化
- mailbox 绑定 assignment

### Phase D：恢复、claim、汇总视图

- lease/claim
- snapshot / blockers / objects 视图
- supervisor 补齐 agent consumer

---

## 11. 非目标

当前 spec 不做：

- 引入数据库或消息队列
- 自动修改 `.kiro/WORKTREE_ASSIGNMENTS.md`
- 替代人工架构决策

---

**最后更新**: 2026-03-07
