# SKILL.md 开发者体验降门槛 — 需求文档

> **Spec**: skill-dx
> **创建日期**: 2026-02-25
> **目标**: 让业务人员用纯自然语言编写 SKILL.md，无需了解 cron 表达式、JSON Schema 或 binding 语法

---

## 背景

OwlClaw 的核心差异化在于"Markdown 即 AI 能力"——业务人员写 SKILL.md 描述业务需求，Agent 自动理解并执行。但当前 SKILL.md 的 `owlclaw:` 扩展字段（cron 表达式、JSON Schema 参数定义、binding 声明）对业务人员来说门槛过高。

要实现"IT 配置一次，业务人员持续受益"的三角色模型（见 `docs/POSITIONING.md` §三），SKILL.md 必须支持纯自然语言书写模式，Agent 运行时负责意图解析。

## 功能需求

### FR-1: 自然语言 SKILL.md 格式

业务人员可以编写不含任何 `owlclaw:` 技术字段的 SKILL.md：

```markdown
---
name: 库存预警
description: 当商品库存低于安全线时提醒我
---

# 库存预警

每天早上 9 点检查一次库存。如果有商品的库存低于安全线，告诉我：
- 哪些商品库存不足
- 当前库存数量和安全库存线
- 建议补货数量（按过去 30 天日均销量 × 7 天）

周五补货数量多算 3 天。A 类商品标记为紧急。
```

Agent 运行时从自然语言中解析出：
- 触发条件（"每天早上 9 点" → cron 调度）
- 所需工具（从已注册的 capabilities 中匹配）
- 业务规则（直接作为 system prompt 传递给 LLM）

### FR-2: SKILL.md 解析器增强

`owlclaw/capabilities/skills.py`（当前 `_parse_skill_file()` 所在文件）需要增强：
- 识别 SKILL.md 是否包含 `owlclaw:` 字段
- 若包含：走现有的结构化解析路径
- 若不包含：走自然语言解析路径（LLM 辅助提取意图）
- 两种模式产出统一的内部 SkillDescriptor 数据结构

### FR-3: 工具自动匹配

当 SKILL.md 不包含显式 binding 时，Agent 运行时应：
1. 从已注册的 capabilities 中搜索语义匹配的工具
2. 通过 LLM function calling 确认匹配结果
3. 将匹配结果缓存，避免重复推理

### FR-4: 触发条件自然语言解析

当 SKILL.md 不包含显式 cron/trigger 配置时：
- "每天早上 9 点" → `0 9 * * *`
- "每周一" → `0 0 * * 1`
- "当收到新订单时" → webhook 或 queue 触发
- 解析由 LLM 完成，结果缓存到 SkillDescriptor

### FR-5: 向后兼容

- 现有包含 `owlclaw:` 字段的 SKILL.md 行为不变
- 自然语言模式是新增路径，不影响已有功能
- 混合模式（部分字段显式、部分自然语言）也应支持

## 非功能需求

- 自然语言解析的 LLM 调用应有缓存机制，避免每次启动都重新解析
- 解析结果应可序列化，支持离线预解析（`owlclaw skill parse --cache`）
- 解析失败时应给出清晰的错误信息，指导用户补充信息

## 分期策略

- **Phase 1**（优先）：触发条件解析 + 缓存 + 双模式路由 + CLI。技术成熟度高，LLM 解析时间表达准确率高。
- **Phase 2**（需用户反馈）：工具语义匹配。embedding 相似度在工具数量多时可能误匹配，需真实场景验证策略后再实现。

## 验收标准

### Phase 1 验收

1. 纯自然语言 SKILL.md 的触发条件可被正确解析为 cron/webhook/queue 配置
2. 现有结构化 SKILL.md 行为不变（回归测试通过）
3. 触发条件解析覆盖常见中英文时间表达
4. 解析结果缓存有效（SHA256 hash 匹配时不重新调用 LLM）

### Phase 2 验收

5. 工具匹配准确率 >= 90%（基于测试用例集）
6. 端到端：纯自然语言 SKILL.md 可被完整加载，Agent 能基于其内容做出决策
