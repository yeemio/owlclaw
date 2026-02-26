# Skills 质量评分与数据飞轮 — 设计文档

> **Spec**: skills-quality
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 数据流架构

```
Ledger Records（已有）
    │
    ▼
QualityAggregator（新增，异步）
    │
    ├─ 按 skill_name 聚合执行指标
    ├─ 计算综合评分
    ├─ 检测质量趋势
    └─ 存储到 SkillQualityStore
    │
    ▼
消费方：
├─ CLI（owlclaw skill quality）
├─ Agent Runtime（工具选择参考）
└─ OwlHub（发布时附带评分）
```

### D-2: QualityAggregator

定时任务（Heartbeat 周期或独立 cron），从 Ledger 中查询最近时间窗口的记录，按 skill 聚合计算指标。

```python
class QualityAggregator:
    async def compute(
        self,
        tenant_id: str,
        skill_name: str,
        window: timedelta = timedelta(days=30),
    ) -> SkillQualityReport:
        records = await self.ledger.query_records(
            tenant_id, LedgerQueryFilters(skill_name=skill_name, since=now - window)
        )
        return SkillQualityReport(
            success_rate=self._calc_success_rate(records),
            avg_latency=self._calc_avg_latency(records),
            avg_cost=self._calc_avg_cost(records),
            intervention_rate=self._calc_intervention_rate(records),
            consistency=self._calc_consistency(records),
            satisfaction=self._calc_satisfaction(records),
            quality_score=self._calc_weighted_score(...),
        )
```

### D-3: 存储策略

- `SkillQualitySnapshot` 表：每次聚合计算的快照（skill_name, tenant_id, window_start, window_end, metrics_json, quality_score, computed_at）
- Lite Mode 下使用内存缓存（`dict[str, SkillQualityReport]`）
- 历史快照用于趋势分析

### D-4: 质量下降检测

```python
def detect_degradation(snapshots: list[SkillQualitySnapshot]) -> bool:
    if len(snapshots) < 3:
        return False
    recent = [s.quality_score for s in snapshots[-3:]]
    return all(recent[i] < recent[i-1] * 0.9 for i in range(1, len(recent)))
```

检测到下降时通过 Signal 触发器通知管理员。

### D-5: Agent Runtime 集成

Agent 在 function calling 选择工具时，VisibilityFilter 可选择性地将质量评分作为工具描述的一部分注入 system prompt，让 LLM 自主考虑质量因素。不硬编码排序规则——符合"AI 决策优先"原则。

### D-6: 文件结构

```
owlclaw/governance/
├── quality_aggregator.py       # 新增：质量指标聚合
├── quality_store.py            # 新增：质量快照存储
└── quality_detector.py         # 新增：质量下降检测

owlclaw/cli/
└── skill_quality.py            # 新增：质量报告 CLI
```

## 依赖

- `owlclaw/governance/ledger.py`（执行记录查询）
- `owlclaw/governance/ledger_inmemory.py`（Lite Mode）
- `owlclaw/agent/runtime/runtime.py`（Agent 工具选择）
- `owlclaw/triggers/signal/`（质量告警通知）

## 不做

- 不做实时评分（批量异步计算即可）
- 不做跨租户评分比较（隐私隔离）
- 不做自动 Skill 修复（仅提供改善建议）
