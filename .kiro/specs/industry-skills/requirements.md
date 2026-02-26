# OwlHub 语义搜索推荐 — 需求文档

> **Spec**: industry-skills（已从"行业 Skills 包"降级为"搜索推荐增强"）
> **创建日期**: 2026-02-25
> **调整日期**: 2026-02-25
> **调整原因**: 自编行业 Skills 缺乏真实业务场景验证，价值存疑。真正有价值的行业 Skills 只能来自真实用户实践。OwlClaw 应做的是：当用户描述需求时，从 OwlHub 已有 Skills + 模板中推荐最匹配的起点。
> **关联**: `docs/POSITIONING.md` §八 生态飞轮

---

## 背景

OwlHub 已有模板库（skill-templates spec，5 类通用模板）和 Skills 索引（owlhub spec），但搜索能力仅限关键词匹配。用户描述"我想让系统每天检查库存"时，应该能直接推荐最匹配的模板作为起点，而不是让用户自己翻目录。

## 功能需求

### FR-1: 语义搜索增强

增强 `owlclaw skill search` 命令，支持自然语言描述匹配：

```bash
# 关键词搜索（现有）
owlclaw skill search inventory

# 语义搜索（新增）
owlclaw skill search --query "我想让系统每天检查库存，低于安全线时提醒我"
```

语义搜索基于 LLM embedding 相似度，从 OwlHub index + 本地模板库中匹配。

### FR-2: 推荐结果排序

搜索结果按相关度排序，展示：
- Skill 名称 + 描述
- 匹配度评分
- 来源（OwlHub / 本地模板）
- 一键安装命令

### FR-3: 行业标签体系

为 OwlHub 的 Skills 和模板增加行业标签（`industry` 字段）：

```yaml
# SKILL.md frontmatter
---
name: inventory-monitor
industry: retail
tags: [monitoring, inventory, alert]
---
```

支持按行业过滤：

```bash
owlclaw skill search --industry retail
owlclaw skill search --industry manufacturing --query "设备维护"
```

### FR-4: 包格式规范（为社区贡献做准备）

定义 `package.yaml` 格式规范，为未来社区贡献的行业 Skills 包提供标准结构：

```yaml
name: retail-skills
version: 1.0.0
industry: retail
description: 零售/电商行业 Agent Skills 包
skills:
  - inventory-alert
  - order-anomaly
requires:
  owlclaw: ">=1.0.0"
```

不自编行业 Skills 内容，仅定义格式规范和安装流程。

## 非功能需求

- 语义搜索的 LLM embedding 调用应有缓存（index 不变则不重新计算）
- 搜索延迟 < 3 秒（含 LLM 调用）
- 无 LLM 时降级为关键词搜索

## 验收标准

1. `owlclaw skill search --query` 可返回语义匹配结果
2. `owlclaw skill search --industry` 可按行业过滤
3. `package.yaml` 格式规范文档化
4. 现有关键词搜索行为不变（回归测试通过）
