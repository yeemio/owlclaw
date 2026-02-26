# OwlHub 语义搜索推荐 — 设计文档

> **Spec**: industry-skills（已降级为搜索推荐增强）
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 搜索架构

```
用户输入（自然语言描述 / 关键词）
    │
    ├─ 关键词模式 → 现有 index 关键词匹配
    └─ 语义模式（--query）→ LLM embedding
    │
    ▼
匹配候选集（OwlHub index + 本地模板）
    │
    ▼
相关度排序 + 行业过滤
    │
    ▼
格式化输出（名称 + 描述 + 评分 + 安装命令）
```

### D-2: Embedding 策略

- 使用 `owlclaw/integrations/llm.py` 的 embedding 接口（litellm.aembedding）
- 预计算 OwlHub index 中所有 Skills 的 embedding，缓存为 `.owlclaw/cache/skill_embeddings.json`
- 用户查询时计算查询 embedding，与缓存做余弦相似度
- 缓存 key = index 内容的 SHA256 hash，index 变更时重新计算

### D-3: 行业标签

在 SKILL.md frontmatter 中增加可选的 `industry` 和 `tags` 字段。SkillParser 解析时提取。OwlHub index.json 中包含这些字段用于过滤。

### D-4: 包格式规范

`package.yaml` 仅定义格式标准，不自编内容。文档化后发布到 `docs/SKILL_PACKAGE_FORMAT.md`，供社区贡献者参考。

### D-5: 文件结构

```
owlclaw/cli/
└── skill_search.py             # 增强：语义搜索

owlclaw/capabilities/
└── skill_parser.py             # 增强：解析 industry/tags 字段

docs/
└── SKILL_PACKAGE_FORMAT.md     # 新增：包格式规范文档
```

## 依赖

- `owlclaw/integrations/llm.py`（embedding 调用）
- `owlclaw/cli/skill.py`（现有搜索命令）
- spec: owlhub（OwlHub index 结构）

## 不做

- 不自编行业 Skills 内容（等社区贡献）
- 不做 Skills 推荐算法（简单余弦相似度即可）
- 不做 OwlHub 服务端搜索（客户端本地计算）
