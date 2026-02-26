# AI 辅助 Skill 生成 — 任务清单

> **Spec**: skill-ai-assist
> **创建日期**: 2026-02-25

---

## Task 1: SkillCreatorAgent 核心

- [ ] 1.1 创建 `owlclaw/capabilities/skill_creator.py`
- [ ] 1.2 实现 system prompt 模板（角色 + capabilities 注入 + 格式规范）
- [ ] 1.3 实现多轮对话状态管理（收集信息 → 澄清 → 确认 → 生成）
- [ ] 1.4 实现信息完整性检查（必填项 / 可选项 / 默认值）
- [ ] 1.5 实现 SKILL.md 文本生成（frontmatter + 正文）
- [ ] 1.6 单元测试：对话流程 + 生成结果校验（mock LLM）

## Task 2: 对话式 CLI

- [ ] 2.1 创建 `owlclaw/cli/skill_create.py`
- [ ] 2.2 实现 `owlclaw skill create --interactive` 命令
- [ ] 2.3 实现终端交互（prompt_toolkit 或 click.prompt）
- [ ] 2.4 实现上下文感知（显示已注册 capabilities）
- [ ] 2.5 实现生成结果预览 + 确认 + 保存
- [ ] 2.6 单元测试：CLI 命令测试

## Task 3: 从文档生成

- [ ] 3.1 创建 `owlclaw/capabilities/skill_doc_extractor.py`
- [ ] 3.2 实现文档读取（Markdown / 纯文本）
- [ ] 3.3 实现 LLM 文档分析（识别可自动化流程）
- [ ] 3.4 实现批量 SKILL.md 生成
- [ ] 3.5 实现 `owlclaw skill create --from-doc` CLI 命令
- [ ] 3.6 单元测试：从示例 SOP 文档生成 Skill

## Task 4: 模板系统

- [ ] 4.1 创建 `owlclaw/cli/skill_templates.py`
- [ ] 4.2 实现本地模板目录管理（`~/.owlclaw/templates/`）
- [ ] 4.3 实现 `owlclaw skill list-templates` 命令
- [ ] 4.4 实现 `owlclaw skill create --from-template` 命令
- [ ] 4.5 创建 3 个内置模板（inventory-monitor / order-processor / report-generator）
- [ ] 4.6 单元测试：模板列出 + 使用

## Task 5: 校验增强

- [ ] 5.1 增强 `skill_validator.py`：工具可用性校验
- [ ] 5.2 增强 `skill_validator.py`：触发条件可解析性校验
- [ ] 5.3 增强 `skill_validator.py`：业务规则歧义检测
- [ ] 5.4 集成测试：端到端对话创建 + 校验 + 解析
