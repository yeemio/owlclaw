# 渐进式迁移（migration_weight）— 需求文档

> **Spec**: progressive-migration
> **创建日期**: 2026-02-25
> **目标**: 通过 `migration_weight` 控制 Agent 接管比例，实现从零风险观察到完全自主的渐进式迁移

---

## 背景

企业将现有业务系统交给 AI Agent 自主决策，最大的阻力是**信任**。即使技术上可行，业务负责人也不会一步到位让 Agent 全权接管——他们需要一个渐进的过程：先观察 Agent 会怎么做，确认安全后逐步放权。

`migration_weight`（0% → 100%）是解决这个信任问题的核心机制。它让企业可以精确控制 Agent 的自主程度，从"只看不做"到"完全接管"，每一步都有审计记录。

这也是 OwlClaw 相对于其他 Agent 框架的关键差异化——没有任何框架提供内置的渐进式迁移机制（见 `docs/POSITIONING.md` §二.5）。

## 功能需求

### FR-1: migration_weight 配置

每个 Skill 可配置 `migration_weight`（0-100 整数）：

```yaml
# owlclaw.yaml
skills:
  inventory-monitor:
    migration_weight: 30    # 30% 自主，70% 仅记录
  order-processor:
    migration_weight: 0     # 纯观察模式
  report-generator:
    migration_weight: 100   # 完全自主
```

也可在 SKILL.md 的 `owlclaw:` 扩展字段中设置：

```markdown
---
name: inventory-monitor
owlclaw:
  migration_weight: 30
---
```

### FR-2: 四个迁移阶段

| 阶段 | weight 范围 | Agent 行为 |
|------|------------|-----------|
| **观察** | 0 | Agent 分析并生成决策建议，但不执行任何操作。决策记录到 Ledger |
| **建议** | 1-49 | Agent 生成决策建议并通知人类审批。按 weight 概率自动执行低风险操作 |
| **协作** | 50-99 | Agent 自动执行大部分操作，高风险操作需人类审批。按 weight 概率决定是否需要审批 |
| **自主** | 100 | Agent 完全自主决策和执行，所有操作记录到 Ledger |

### FR-3: 风险评估集成

Agent 在决策时结合 `migration_weight` 和操作风险等级：

```
实际执行概率 = migration_weight × (1 - risk_level)
```

- `risk_level` 由治理层根据操作类型、金额、影响范围评估
- 高风险操作（如大额采购）即使 weight=80 也可能需要人类审批
- 低风险操作（如发送通知）在 weight=20 时也可能自动执行

### FR-4: 审批工作流

当操作需要人类审批时：
1. Agent 生成决策建议（包含推理过程）
2. 通过配置的通知渠道发送审批请求
3. 人类审批（approve / reject / modify）
4. 审批结果记录到 Ledger
5. 若 approve：Agent 执行操作
6. 若 reject：Agent 记录原因，不执行
7. 若 modify：Agent 按修改后的参数执行

### FR-5: 自动升级建议

基于 Ledger 中的历史数据，Agent 可建议调整 `migration_weight`：

```
Agent 'inventory-monitor' 在过去 30 天内：
- 总决策数：150
- 人类审批通过率：98%
- 人类修改率：1.3%
- 建议：将 migration_weight 从 30 提升到 50
```

### FR-6: Ledger 审计增强

Ledger 记录需增加迁移相关字段：
- `migration_weight`：决策时的 weight 值
- `execution_mode`：`auto` / `pending_approval` / `approved` / `rejected`
- `risk_level`：操作风险等级
- `approval_by`：审批人（若有）
- `approval_time`：审批时间（若有）

## 非功能需求

- `migration_weight` 变更应实时生效（无需重启）
- 审批请求超时（可配置，默认 24 小时）后自动标记为 expired
- 所有迁移阶段变更记录到 Ledger，支持合规审计

## 验收标准

1. weight=0 时 Agent 不执行任何操作，仅记录决策建议
2. weight=100 时 Agent 完全自主执行
3. 中间值时按概率模型决定自动执行或请求审批
4. Ledger 完整记录所有迁移相关信息
5. `migration_weight` 变更实时生效
