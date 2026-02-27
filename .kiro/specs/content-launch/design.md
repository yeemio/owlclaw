# 内容营销启动 — 设计文档

> **Spec**: content-launch
> **阶段**: Phase 8.3

---

## 1. 第一篇文章选题

三个候选方向（从决策文档 §6.7）：

| 方向 | 标题 | 目标读者 | 发布渠道 |
|------|------|---------|---------|
| A | "How I stopped my AI app from burning $50/day on runaway LLM calls" | OpenClaw 用户、独立开发者 | HN Show HN, Reddit |
| B | "I replaced APScheduler with Hatchet and my tasks stopped disappearing" | Python 开发者 | HN, Reddit /r/python |
| C | "One command to connect OpenClaw to your business database" | OpenClaw 用户 | Reddit /r/openclaw |

**选择策略**：Phase 8.1 完成后根据 Mionyee 真实数据选择最有说服力的方向。如果治理数据更震撼选 A，如果调度迁移更顺利选 B。

## 2. 文章结构模板

```markdown
# [标题：解决一个具体问题]

## The Problem
[用第一人称讲述遇到的问题，附真实数据]

## What I Tried
[列举尝试过的方案和为什么不行]

## My Solution
[介绍解决方案，附代码片段]

## Results
[真实数据对比：before vs after，附截图/图表]

## Try It Yourself
[3 步上手指南：pip install → 配置 → 运行]

## What's Next
[引导到 GitHub 仓库和更多资源]
```

## 3. Mionyee 案例材料结构

```markdown
# OwlClaw 实战案例：Mionyee 交易系统 AI 治理升级

## 背景
- 系统概况（28 个 AI 服务、48 个定时任务）
- 遇到的问题（成本失控、调度脆弱）

## 方案
- 治理叠加（预算/限流/熔断）
- 调度迁移（APScheduler → Hatchet）

## 实施过程
- 改动量（X 行胶水代码）
- 实施周期（Y 天）

## 结果
- 成本：月 LLM 费用从 $X 降至 $Y（降低 Z%）
- 稳定性：任务丢失率从 A% 降至 0%
- 审计：100% 调用可追溯

## 技术细节
[附配置示例和关键代码]
```

## 4. 咨询方案模板结构

```markdown
# AI 智能化转型方案 — [客户名称]

## 一、现状调研
- 现有系统清单
- AI 可行性评估
- 痛点优先级排序

## 二、方案设计
- 接入模式选择（增强/代理）
- 场景选择（报表解读/客户跟进/库存预警）
- 技术方案（OwlClaw 配置 + SKILL.md + 治理规则）

## 三、实施计划
- 里程碑和时间线
- 交付物清单
- 验收标准

## 四、投资与回报
- 项目费用：¥[X]
- 预期回报：[具体可量化指标]
- 月维护费：¥[Y]（可选）

## 五、风险与缓解
- Shadow 模式验证
- 回滚方案
```

## 5. 发布策略

| 渠道 | 内容 | 时间 | 说明 |
|------|------|------|------|
| Reddit /r/openclaw | 方向 C 教程 | Phase 8.2 完成后 | OpenClaw 用户最直接 |
| Hacker News Show HN | 方向 A 或 B | Phase 8.2 完成后 | 周二上午发布（流量高峰） |
| 掘金 | 中文版 | 同步 | 国内开发者 |
| V2EX | 中文版 | 同步 | /t/python 或 /t/ai |

## 6. 后续内容节奏

Phase 8.3 之后：每 2 周 1 篇技术文章。内容来源：
- 每次解决一个技术问题 → 写一篇文章
- 每次咨询客户的问题 → 提炼成一篇文章
- 社区回答超过 200 字 → 扩展成文章
