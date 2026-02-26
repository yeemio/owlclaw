# SKILL.md 开发者体验降门槛 — 设计文档

> **Spec**: skill-dx
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 双模式解析架构

SkillParser 采用双模式设计：

```
SKILL.md 输入
    │
    ├─ 检测 owlclaw: 字段存在？
    │   ├─ 是 → 结构化解析（现有路径）
    │   └─ 否 → 自然语言解析（新增路径）
    │
    ▼
统一的 SkillDescriptor
```

两条路径产出相同的 `SkillDescriptor` 数据结构，下游（Agent Runtime、Governance、Trigger 注册）无需感知差异。

### D-2: 自然语言解析流程

```
1. 读取 SKILL.md 全文
2. 提取 frontmatter（name, description）
3. 将正文发送给 LLM，prompt 要求提取：
   - trigger_intent: 触发条件的自然语言描述
   - tool_intent: 需要的工具能力描述列表
   - business_rules: 业务规则列表（直接保留原文）
4. trigger_intent → 调用 trigger_resolver 转换为 cron/webhook/queue 配置
5. tool_intent → 调用 capability_matcher 从已注册工具中匹配
6. 组装为 SkillDescriptor
```

### D-3: 缓存策略

- 解析结果以 `{skill_name}.parsed.json` 缓存在 `.owlclaw/cache/` 目录
- 缓存 key = SKILL.md 内容的 SHA256 hash
- 启动时检查缓存：hash 匹配则直接加载，不匹配则重新解析
- CLI 命令 `owlclaw skill parse --cache` 支持离线预解析

### D-4: 工具匹配算法

```
1. 从 tool_intent 列表中提取关键词
2. 与已注册 capabilities 的 name + description 做语义匹配
3. 匹配方式：
   a. 精确名称匹配（优先级最高）
   b. LLM embedding 相似度匹配（阈值 >= 0.8）
   c. LLM function calling 确认（最终裁决）
4. 匹配结果写入 SkillDescriptor.resolved_tools
```

### D-5: 触发条件解析

trigger_resolver 使用 LLM 将自然语言时间表达转换为结构化配置：

| 自然语言 | 解析结果 |
|---------|---------|
| "每天早上 9 点" | `{"type": "cron", "expression": "0 9 * * *"}` |
| "每周一" | `{"type": "cron", "expression": "0 0 * * 1"}` |
| "当收到新订单时" | `{"type": "webhook", "event": "order.created"}` |
| "库存变化时" | `{"type": "db_change", "table": "inventory"}` |

解析结果包含 confidence 分数，低于阈值时提示用户确认。

### D-6: 文件结构

```
owlclaw/capabilities/
├── skill_parser.py          # 增强：双模式解析入口
├── skill_nl_parser.py       # 新增：自然语言解析器
├── trigger_resolver.py      # 新增：触发条件自然语言解析
└── capability_matcher.py    # 新增：工具语义匹配
```

## 依赖

- `owlclaw/integrations/llm.py`（LLM 调用）
- `owlclaw/capabilities/skill_parser.py`（现有解析器）
- `owlclaw/capabilities/registry.py`（已注册 capabilities）

## 不做

- 不做 SKILL.md 的 GUI 编辑器（CLI + 文本编辑器优先）
- 不做多语言翻译（支持中英文自然语言输入，但不做自动翻译）
- 不做 SKILL.md 版本管理（由 Git 管理）
