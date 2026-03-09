# Audit Workflow Protocol

## 目的

规范 `audit-a`（深度审计）与 `audit-b`（审计复核）的工作边界，防止两类失真：

- 只读文档不读代码的假审计
- 越权直接改代码的假修复

审计窗口的唯一职责是：**读代码、找问题、提交结构化 findings 给 `main`**。

---

## 角色定义

### `audit-a`

- 角色：深度审计
- 方法：必须按 `deep-codebase-audit` skill 做多维度代码审计
- 必须覆盖：
  - 4 个审计维度：`core_logic`、`lifecycle_integrations`、`io_boundaries`、`data_security`
  - 5 个 thinking lenses：`correctness`、`failure`、`adversary`、`drift`、`omission`

### `audit-b`

- 角色：审计复核
- 方法：必须按 `deep-codebase-audit` skill 对本轮审计做独立复核
- 必须做到：
  - 重新读代码验证已有 finding
  - 主动继续找漏项
  - 不能只复述 `audit-a` 报告

---

## 非法行为

以下行为均视为协议违规：

- 只看文档、报告、spec，不读代码
- 只复述已有 finding，不做代码复核
- 直接修改仓库代码
- 直接给 `review` / `codex` / `codex-gpt` 派任务
- 只输出自然语言结论，不落结构化 finding

---

## 合法输出

审计窗口只允许两类输出：

1. 更新审计状态

```powershell
poetry run python scripts/workflow_audit_state.py update --agent audit-a --status started --summary "auditing runtime" --file-read owlclaw/agent/runtime/runtime.py --dimension-covered core_logic --lines-read 400
```

2. 提交结构化 finding

```powershell
poetry run python scripts/workflow_audit_state.py finding `
  --agent audit-a `
  --title "Observation tool leaks unsanitized args" `
  --summary "Tool output flows into prompt without sanitizer." `
  --severity p1 `
  --spec workflow-closed-loop `
  --task-ref 3.3 `
  --target-agent codex `
  --target-branch codex-work `
  --file owlclaw/agent/runtime/runtime.py `
  --dimension core_logic `
  --lens adversary `
  --evidence "Traced tool result into runtime._build_messages() without sanitizer."
```

---

## 强制字段

所有 audit finding 必须带：

- `file`
  说明审计真正读了哪段代码
- `dimension`
  说明该问题属于哪个审计维度
- `lens`
  说明通过哪个 thinking lens 发现
- `evidence`
  说明具体代码证据或数据流证据

协议层会拒绝缺这些字段的 audit finding。

---

## 闭环关系

- `audit-a` / `audit-b` 只能写 `finding`
- `main` 消费 finding，决定 triage / assignment
- `codex` / `codex-gpt` 只消费 `assignment`
- `review` 只消费 `delivery`，并写 `review_verdict`
- `main` 再消费 `review_verdict` / `merge_decision`

审计是输入源，不是修复者。
