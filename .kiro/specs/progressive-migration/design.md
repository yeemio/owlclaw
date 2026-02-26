# 渐进式迁移（migration_weight）— 设计文档

> **Spec**: progressive-migration
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 决策拦截点

`migration_weight` 在 Agent Runtime 的决策执行链路中作为拦截点：

```
Agent 决策（function calling）
    │
    ▼
MigrationGate（新增）
    │
    ├─ 读取 skill 的 migration_weight
    ├─ 评估操作风险等级
    ├─ 计算执行概率
    │
    ├─ 自动执行 → 正常执行链路
    ├─ 需要审批 → ApprovalQueue
    └─ 仅记录 → Ledger（不执行）
    │
    ▼
Ledger 记录（所有路径都记录）
```

### D-2: MigrationGate 组件

```python
class MigrationGate:
    """Intercepts agent decisions based on migration_weight."""

    async def evaluate(
        self,
        skill_name: str,
        action: AgentAction,
        context: ExecutionContext,
    ) -> MigrationDecision:
        weight = self._get_weight(skill_name)
        risk = await self._assess_risk(action, context)
        probability = weight * (1.0 - risk) / 100.0

        if weight == 0:
            return MigrationDecision.OBSERVE_ONLY
        if weight == 100:
            return MigrationDecision.AUTO_EXECUTE
        if random.random() < probability:
            return MigrationDecision.AUTO_EXECUTE
        return MigrationDecision.REQUIRE_APPROVAL
```

### D-3: 风险评估

风险等级由 `RiskAssessor` 评估，基于：

| 因素 | 权重 | 示例 |
|------|------|------|
| 操作类型 | 0.3 | 读取=0.0, 通知=0.2, 写入=0.5, 删除=0.8, 支付=1.0 |
| 影响范围 | 0.3 | 单条记录=0.1, 批量=0.5, 全表=1.0 |
| 金额 | 0.2 | <1000=0.1, <10000=0.5, >=10000=1.0 |
| 可逆性 | 0.2 | 可撤销=0.0, 部分可撤销=0.5, 不可逆=1.0 |

风险等级 = 各因素加权和，范围 [0.0, 1.0]。

操作类型和影响范围由 SKILL.md 的 binding 信息推断（HTTP GET=读取，POST=写入，DELETE=删除）。金额和可逆性由 SKILL.md 的业务规则或 `owlclaw:` 扩展字段声明。

### D-4: 审批队列

```
ApprovalQueue
    │
    ├─ 存储：Ledger 表扩展（新增 approval_status 字段）
    ├─ 通知：通过 Trigger 层的 Signal 触发器发送
    ├─ 审批接口：CLI / API / Webhook callback
    └─ 超时：可配置，默认 24h，超时标记 expired
```

Lite Mode 下审批队列使用 InMemoryLedger，审批通过 CLI 交互完成。

### D-5: 配置热更新

`migration_weight` 支持运行时热更新：
- 配置源：`owlclaw.yaml` 文件监听（watchdog）或 API 调用
- 更新粒度：per-skill
- 生效时间：下一次决策即生效（无需重启）

### D-6: 文件结构

```
owlclaw/governance/
├── migration_gate.py           # 新增：迁移决策拦截
├── risk_assessor.py            # 新增：风险评估
├── approval_queue.py           # 新增：审批队列
└── ledger.py                   # 增强：迁移审计字段

owlclaw/agent/
└── runtime.py                  # 修改：集成 MigrationGate
```

## 依赖

- `owlclaw/governance/ledger.py`（Ledger 记录）
- `owlclaw/governance/ledger_inmemory.py`（Lite Mode 支持）
- `owlclaw/agent/runtime.py`（Agent 决策链路）
- `owlclaw/triggers/signal.py`（审批通知）

## 不做

- 不做审批的 Web UI（CLI + API 优先）
- 不做自动 weight 调整（仅提供建议，调整由人类决定）
- 不做跨 Skill 的全局 weight（每个 Skill 独立配置）
