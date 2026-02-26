# SKILL.md 开发者体验降门槛 — 任务清单

> **Spec**: skill-dx
> **创建日期**: 2026-02-25
> **分期策略**: Phase 1 触发解析+缓存（确定性高），Phase 2 工具匹配（需真实用户反馈后决定策略）

---

## Phase 1：触发条件解析 + 缓存（优先实现）

### Task 1: SkillDescriptor 数据结构统一

- [x] 1.1 审查现有 `SkillDescriptor` 数据结构，确认可承载自然语言解析结果
- [x] 1.2 增加 `parse_mode` 字段（`structured` / `natural_language` / `hybrid`）
- [x] 1.3 增加 `trigger_config` 字段（解析后的触发配置）
- [x] 1.4 单元测试：SkillDescriptor 序列化/反序列化

### Task 2: 自然语言解析器（基础）

- [x] 2.1 创建 `owlclaw/capabilities/skill_nl_parser.py`
- [x] 2.2 实现 SKILL.md 模式检测（有无 `owlclaw:` 字段）
- [x] 2.3 实现 LLM 意图提取（trigger_intent / business_rules）
- [x] 2.4 实现解析结果缓存（SHA256 hash + `.owlclaw/cache/`）
- [x] 2.5 单元测试：自然语言 SKILL.md 解析（mock LLM）

### Task 3: 触发条件解析器

- [x] 3.1 创建 `owlclaw/capabilities/trigger_resolver.py`
- [x] 3.2 实现中英文时间表达 → cron 表达式转换（LLM 辅助）
- [x] 3.3 实现事件表达 → webhook/queue/db_change 配置转换
- [x] 3.4 实现 confidence 分数 + 低置信度提示
- [x] 3.5 单元测试：覆盖常见时间和事件表达

### Task 5: SkillParser 集成（Phase 1 部分）

- [x] 5.1 修改 `skills.py` 的 `_parse_skill_file()` 增加双模式路由
- [x] 5.2 集成 skill_nl_parser + trigger_resolver
- [ ] 5.3 实现混合模式（部分结构化 + 部分自然语言）
- [ ] 5.4 集成测试：自然语言 SKILL.md 触发条件解析端到端

### Task 6: CLI 支持

- [x] 6.1 实现 `owlclaw skill parse` 命令（显示解析结果）
- [x] 6.2 实现 `owlclaw skill parse --cache` 离线预解析
- [ ] 6.3 实现 `owlclaw skill validate` 增强（支持自然语言模式校验）
- [ ] 6.4 单元测试：CLI 命令测试

---

## Phase 2：工具语义匹配（需真实用户反馈后启动）

> **启动条件**: Phase 1 上线后收集用户反馈，确认工具匹配策略再实现。
> **风险点**: embedding 相似度在工具数量多时可能误匹配，需要真实场景验证匹配策略。

### Task 1-ext: SkillDescriptor 扩展

- [ ] 1.5 增加 `resolved_tools` 字段（工具匹配结果）

### Task 4: 工具语义匹配器

- [ ] 4.1 创建 `owlclaw/capabilities/capability_matcher.py`
- [ ] 4.2 实现精确名称匹配
- [ ] 4.3 实现 embedding 相似度匹配（复用 memory embedder）
- [ ] 4.4 实现 LLM function calling 确认匹配
- [ ] 4.5 单元测试：工具匹配准确率测试用例集

### Task 5-ext: SkillParser 集成（Phase 2 部分）

- [ ] 5.5 集成 capability_matcher 到 SkillParser
- [ ] 5.6 集成测试：端到端自然语言 SKILL.md 加载（含工具匹配）
