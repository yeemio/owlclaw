# Skills 质量评分与数据飞轮 — 任务清单

> **Spec**: skills-quality
> **创建日期**: 2026-02-25

---

## Task 1: 执行指标采集

- [x] 1.1 创建 `owlclaw/governance/quality_aggregator.py`
- [x] 1.2 实现 6 项指标计算（成功率/延迟/成本/干预率/一致性/满意度）
- [x] 1.3 实现加权综合评分计算（权重可配置）
- [x] 1.4 实现时间窗口聚合（日/周/月）
- [x] 1.5 单元测试：各指标计算 + 综合评分

## Task 2: 质量存储

- [x] 2.1 创建 `owlclaw/governance/quality_store.py`
- [x] 2.2 实现 `SkillQualitySnapshot` 数据模型
- [x] 2.3 实现数据库存储（SQLAlchemy 模型 + Alembic 迁移）
- [x] 2.4 实现内存存储（Lite Mode）
- [x] 2.5 单元测试：存储和查询

## Task 3: 质量趋势与告警

- [x] 3.1 创建 `owlclaw/governance/quality_detector.py`
- [x] 3.2 实现质量下降检测（连续 3 窗口下降 > 10%）
- [x] 3.3 实现质量改善建议生成（基于最差指标）
- [x] 3.4 实现 Signal 触发器告警通知
- [x] 3.5 单元测试：下降检测 + 建议生成

## Task 4: CLI 支持

- [x] 4.1 创建 `owlclaw/cli/skill_quality.py`
- [x] 4.2 实现 `owlclaw skill quality <name>` 单 Skill 报告
- [x] 4.3 实现 `owlclaw skill quality --all` 全局概览
- [x] 4.4 实现 `owlclaw skill quality --trend` 趋势展示
- [x] 4.5 实现 `owlclaw skill quality --suggest` 改善建议
- [x] 4.6 单元测试：CLI 命令

## Task 5: Agent Runtime 集成

- [x] 5.1 修改 VisibilityFilter：可选注入质量评分到工具描述
- [x] 5.2 实现质量评分缓存（避免每次决策都查询）
- [x] 5.3 集成测试：Agent 决策参考质量评分

## Task 6: OwlHub 集成

- [ ] 6.1 Skills 发布时附带匿名聚合质量评分
- [ ] 6.2 OwlHub 搜索结果支持按质量评分排序
- [ ] 6.3 低质量 Skills 标记警告
