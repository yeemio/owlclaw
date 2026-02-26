# Skills 质量评分与数据飞轮 — 需求文档

> **Spec**: skills-quality
> **创建日期**: 2026-02-25
> **目标**: 基于 Agent 执行数据构建 Skills 质量评分体系，驱动 OwlHub 推荐优化和 Agent 决策改进
> **关联**: `docs/POSITIONING.md` §八 数据飞轮第 3 层

---

## 背景

POSITIONING.md 承诺了三层飞轮，其中第 3 层"数据飞轮"是：

> Agent 运行数据 → Skills 质量评分 → 推荐优化 → Agent 决策更准

Ledger 已经记录了每次 Agent 决策的完整数据（工具调用、耗时、成本、成功/失败），但这些数据目前只用于审计，没有被消费来反哺 Skills 质量。这是从"能用"到"好用"的关键闭环。

## 功能需求

### FR-1: Skills 执行指标采集

从 Ledger 记录中提取每个 Skill 的执行指标：

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| 成功率 | 成功执行 / 总执行 | 基础质量信号 |
| 平均延迟 | 执行耗时均值 | 性能指标 |
| 平均成本 | LLM token 成本均值 | 效率指标 |
| 人工干预率 | 需要人工审批或修正 / 总执行 | 自主程度指标 |
| 决策一致性 | 相同输入下决策方差 | 稳定性指标 |
| 用户满意度 | 审批通过率 + 修改率 | 间接满意度 |

### FR-2: Skills 质量评分模型

综合评分 = 加权组合：

```
quality_score = w1 × success_rate + w2 × (1 - latency_norm) + w3 × (1 - cost_norm) 
              + w4 × (1 - intervention_rate) + w5 × consistency + w6 × satisfaction
```

- 评分范围：0.0 ~ 1.0
- 权重可配置（`owlclaw.yaml` 中的 `quality_weights`）
- 默认权重：成功率 0.3、干预率 0.25、满意度 0.2、一致性 0.15、延迟 0.05、成本 0.05

### FR-3: 质量趋势追踪

- 按时间窗口（日/周/月）计算质量评分趋势
- 检测质量下降（连续 3 个窗口评分下降 > 10%）并告警
- 质量改善建议（基于最差指标给出优化方向）

### FR-4: OwlHub 集成

- Skills 发布到 OwlHub 时附带质量评分（匿名聚合，不暴露企业数据）
- OwlHub 搜索结果按质量评分排序
- 质量评分低于阈值的 Skills 标记警告

### FR-5: CLI 支持

```bash
owlclaw skill quality <skill-name>          # 查看单个 Skill 质量报告
owlclaw skill quality --all                 # 查看所有 Skills 质量概览
owlclaw skill quality --trend --period 30d  # 查看 30 天质量趋势
owlclaw skill quality --suggest             # 查看质量改善建议
```

### FR-6: Agent 决策反馈闭环

Agent Runtime 在选择工具时，可参考 Skills 质量评分：
- 多个 Skill 可完成同一任务时，优先选择质量评分更高的
- 质量评分低于阈值的 Skill 在 Agent 决策时降低优先级（非屏蔽）

## 非功能需求

- 质量评分计算应异步进行，不影响 Agent 决策延迟
- 评分数据存储在 Ledger 扩展表中，复用现有数据库基础设施
- 隐私保护：发布到 OwlHub 的评分为匿名聚合数据

## 验收标准

1. 可从 Ledger 数据计算出 6 项执行指标
2. 综合评分模型可配置权重
3. CLI 可展示质量报告和趋势
4. 质量下降告警可触发
