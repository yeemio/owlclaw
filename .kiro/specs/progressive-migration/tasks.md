# 渐进式迁移（migration_weight）— 任务清单

> **Spec**: progressive-migration
> **创建日期**: 2026-02-25

---

## Task 1: MigrationGate 核心

- [ ] 1.1 创建 `owlclaw/governance/migration_gate.py`
- [ ] 1.2 实现 `MigrationDecision` 枚举（OBSERVE_ONLY / AUTO_EXECUTE / REQUIRE_APPROVAL）
- [ ] 1.3 实现 `MigrationGate.evaluate()` 决策逻辑
- [ ] 1.4 实现 `migration_weight` 配置读取（owlclaw.yaml + SKILL.md）
- [ ] 1.5 实现配置热更新（文件监听 / API）
- [ ] 1.6 单元测试：各阶段决策行为（weight=0/30/70/100）

## Task 2: 风险评估器

- [ ] 2.1 创建 `owlclaw/governance/risk_assessor.py`
- [ ] 2.2 实现操作类型推断（从 binding 信息：HTTP method / SQL type）
- [ ] 2.3 实现影响范围评估
- [ ] 2.4 实现加权风险计算
- [ ] 2.5 实现 SKILL.md `owlclaw:` 扩展字段中的风险声明解析
- [ ] 2.6 单元测试：各风险因素组合

## Task 3: 审批队列

- [ ] 3.1 创建 `owlclaw/governance/approval_queue.py`
- [ ] 3.2 实现审批请求创建（包含决策建议 + 推理过程）
- [ ] 3.3 实现审批状态管理（pending / approved / rejected / modified / expired）
- [ ] 3.4 实现审批超时机制
- [ ] 3.5 实现 InMemoryApprovalQueue（Lite Mode 支持）
- [ ] 3.6 单元测试：审批流程全链路

## Task 4: Ledger 审计增强

- [ ] 4.1 扩展 `LedgerRecord` 数据模型（migration_weight / execution_mode / risk_level / approval_by / approval_time）
- [ ] 4.2 扩展 `InMemoryLedger` 支持新字段
- [ ] 4.3 扩展 `LedgerQueryFilters` 支持按 execution_mode 过滤
- [ ] 4.4 单元测试：新字段记录和查询

## Task 5: Agent Runtime 集成

- [ ] 5.1 修改 `owlclaw/agent/runtime.py`：在决策执行前插入 MigrationGate
- [ ] 5.2 实现 OBSERVE_ONLY 路径（记录但不执行）
- [ ] 5.3 实现 REQUIRE_APPROVAL 路径（发送审批请求 + 等待/异步）
- [ ] 5.4 集成测试：端到端迁移决策流程

## Task 6: CLI 支持

- [ ] 6.1 实现 `owlclaw migration status` 命令（显示各 Skill 的 weight 和统计）
- [ ] 6.2 实现 `owlclaw migration set <skill> <weight>` 命令（运行时调整）
- [ ] 6.3 实现 `owlclaw migration suggest` 命令（基于历史数据的升级建议）
- [ ] 6.4 实现 `owlclaw approval list` / `owlclaw approval approve <id>` 命令
- [ ] 6.5 单元测试：CLI 命令测试
