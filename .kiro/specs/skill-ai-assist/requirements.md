# AI 辅助 Skill 生成 — 需求文档

> **Spec**: skill-ai-assist
> **创建日期**: 2026-02-25
> **目标**: 通过对话式交互引导业务人员创建 SKILL.md，零技术门槛
> **前置依赖**: spec: skill-dx（自然语言 SKILL.md 解析能力）

---

## 背景

即使 SKILL.md 支持纯自然语言书写（spec: skill-dx），业务人员仍然面临"空白页恐惧"——不知道该写什么、怎么组织、写到什么程度算够。

AI 辅助 Skill 生成通过对话式交互解决这个问题：业务人员用自然语言描述需求，AI 引导补充细节，最终自动生成完整的 SKILL.md。这是实现"IT 配置一次，业务人员持续受益"（见 `docs/POSITIONING.md` §三）的关键一环。

## 功能需求

### FR-1: 对话式 Skill 创建 CLI

提供 `owlclaw skill create --interactive` 命令，启动对话式创建流程：

```
$ owlclaw skill create --interactive

OwlClaw Skill Creator

请描述你想让 Agent 做什么：
> 我想让系统每天检查一下库存，如果有商品快没了就提醒我

好的，我理解你需要一个库存监控能力。让我确认几个细节：

1. 检查频率：你说"每天"，具体是什么时间？
> 早上 9 点吧

2. "快没了"的标准是什么？
> 低于安全库存线的 120%

3. 提醒方式是什么？
> 发邮件给我就行

4. 有什么特殊规则吗？比如周末、节假日？
> 周末不用检查

已生成 SKILL.md，保存到 skills/inventory-monitor/SKILL.md
要查看生成的内容吗？(y/n)
```

### FR-2: 上下文感知

对话过程中，AI 应感知已注册的 capabilities：
- 自动推荐可用的工具（"我看到系统已经有 `get_inventory_levels` 和 `send_email` 工具"）
- 提示缺失的工具（"你提到了发邮件，但系统中还没有邮件发送工具，需要 IT 团队先配置"）

### FR-3: 从已有文档生成

支持从已有业务文档（SOP、流程说明）批量生成 SKILL.md：

```bash
owlclaw skill create --from-doc business_process.md --output skills/
```

AI 读取文档，识别可自动化的业务流程，为每个流程生成一个 SKILL.md。

### FR-4: Skill 模板库

提供行业通用模板，降低起步门槛：

```bash
owlclaw skill list-templates
owlclaw skill create --from-template inventory-monitor
```

模板来源：OwlHub 或本地 `~/.owlclaw/templates/`。

### FR-5: 生成质量校验

生成的 SKILL.md 自动经过校验：
- 结构完整性（name、description 必填）
- 工具可用性（引用的工具是否已注册）
- 触发条件可解析性（自然语言时间表达是否可转换）
- 业务规则清晰度（是否有歧义表达需要澄清）

## 非功能需求

- 对话式创建应支持中英文混合输入
- 单次对话轮数不超过 10 轮（避免用户疲劳）
- 生成结果应可编辑（生成后用户可手动调整）
- LLM 调用应使用 OwlClaw 自身的 `owlclaw/integrations/llm.py`

## 验收标准

1. `owlclaw skill create --interactive` 可通过 3-5 轮对话生成有效 SKILL.md
2. 生成的 SKILL.md 可被 SkillParser 正确解析（结构化或自然语言模式）
3. `--from-doc` 可从标准 SOP 文档中提取至少 1 个可用 Skill
4. `--from-template` 可列出并使用模板
