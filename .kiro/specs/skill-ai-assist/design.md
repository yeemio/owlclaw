# AI 辅助 Skill 生成 — 设计文档

> **Spec**: skill-ai-assist
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: 对话引擎架构

对话式 Skill 创建基于 LLM multi-turn conversation：

```
用户输入（自然语言描述）
    │
    ▼
SkillCreatorAgent（LLM + system prompt）
    │
    ├─ 提取意图（做什么、什么时候、怎么通知）
    ├─ 查询已注册 capabilities（上下文感知）
    ├─ 生成澄清问题（补充缺失信息）
    └─ 生成 SKILL.md（当信息充分时）
    │
    ▼
SkillValidator 校验
    │
    ▼
输出 SKILL.md 文件
```

### D-2: System Prompt 设计

SkillCreatorAgent 的 system prompt 包含：
1. 角色定义：你是 OwlClaw Skill 创建助手
2. 已注册 capabilities 列表（动态注入）
3. SKILL.md 格式规范（frontmatter + 正文结构）
4. 对话策略：先理解意图 → 补充细节 → 确认 → 生成

### D-3: 信息完整性检查

生成 SKILL.md 前，确保以下信息已收集：

| 信息项 | 必填 | 示例 |
|--------|------|------|
| 做什么（核心意图） | 是 | "检查库存" |
| 什么时候做（触发条件） | 是 | "每天早上 9 点" |
| 做完怎么通知（输出方式） | 否 | "发邮件" |
| 特殊规则 | 否 | "周末不检查" |
| 异常处理 | 否 | "连续 3 天库存不足升级为紧急" |

缺失必填项时生成澄清问题，缺失可选项时使用合理默认值。

### D-4: 从文档生成流程

```
业务文档（SOP/流程说明）
    │
    ▼
LLM 文档分析
    │
    ├─ 识别可自动化的业务流程
    ├─ 为每个流程提取：意图、触发条件、工具需求、规则
    └─ 生成 SKILL.md 列表
    │
    ▼
用户确认/编辑
    │
    ▼
输出 SKILL.md 文件集
```

### D-5: 模板系统

```
~/.owlclaw/templates/           # 本地模板目录
├── inventory-monitor.md
├── order-processor.md
└── report-generator.md

owlhub://templates/             # 远程模板（OwlHub）
├── industry/retail/
├── industry/manufacturing/
└── industry/finance/
```

模板是预填充的 SKILL.md，用户基于模板修改比从零开始更容易。

### D-6: 文件结构

```
owlclaw/cli/
├── skill_create.py             # 新增：对话式创建 CLI 入口
├── skill_templates.py          # 新增：模板管理
├── skill_validate.py           # 增强：校验生成结果（已有文件）

owlclaw/capabilities/
├── skill_creator.py            # 新增：SkillCreatorAgent 核心逻辑
├── skill_doc_extractor.py      # 新增：从文档提取 Skill（Phase 2）

owlclaw/templates/skills/
└── validator.py                # 增强：模板校验规则（已有文件）
```

## 依赖

- spec: skill-dx（自然语言 SKILL.md 解析能力）
- `owlclaw/integrations/llm.py`（LLM 调用）
- `owlclaw/capabilities/registry.py`（已注册 capabilities 查询）

## 不做

- 不做 Web UI 对话界面（CLI 优先）
- 不做 SKILL.md 的自动部署（生成后由用户手动放置或 `owlclaw skill install`）
- 不做多人协作编辑
