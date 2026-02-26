# OwlHub 语义搜索推荐 — 任务清单

> **Spec**: industry-skills（已降级为搜索推荐增强）
> **创建日期**: 2026-02-25

---

## Task 1: 语义搜索

- [x] 1.1 增强 `owlclaw/cli/skill_hub.py`：扩展 `--query` 语义搜索入口
- [x] 1.2 实现 LLM embedding 调用（复用 `owlclaw.agent.memory.embedder_litellm`）
- [x] 1.3 实现 OwlHub index + 本地模板的 embedding 预计算与缓存
- [x] 1.4 实现余弦相似度匹配 + 排序
- [x] 1.5 实现无 LLM 时降级为关键词搜索
- [x] 1.6 单元测试：语义搜索（mock embedding）

## Task 2: 行业标签

- [x] 2.1 增强 SkillParser：解析 `industry` / `tags` 字段
- [x] 2.2 增强 OwlHub index.json 结构：包含 industry/tags
- [x] 2.3 实现 `owlclaw skill search --industry` 过滤
- [x] 2.4 单元测试：标签解析 + 过滤

## Task 3: 包格式规范

- [x] 3.1 编写 `docs/SKILL_PACKAGE_FORMAT.md`（package.yaml 格式规范）
- [x] 3.2 实现 `owlclaw skill install` 对 package.yaml 的支持
- [x] 3.3 单元测试：包安装流程
