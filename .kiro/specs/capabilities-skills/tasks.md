# 任务清单

## 文档联动

- requirements: `.kiro/specs/capabilities-skills/requirements.md`
- design: `.kiro/specs/capabilities-skills/design.md`
- tasks: `.kiro/specs/capabilities-skills/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Task 0: 契约与文档

- [x] 0.1 确认 requirements.md 完整且与架构文档一致
- [x] 0.2 确认 design.md 完整且包含所有组件设计
- [x] 0.3 确认 tasks.md 覆盖所有需求的实现

## Task 1: Skills_Loader 实现

- [x] 1.1 实现 Skill 数据类
  - [x] 1.1.1 定义 Skill 类（name、description、file_path、metadata、owlclaw_config）
  - [x] 1.1.2 实现 task_type、constraints、trigger 属性
  - [x] 1.1.3 实现 load_full_content() 方法（懒加载）
  - [x] 1.1.4 实现 references_dir 和 scripts_dir 属性
  - [x] 1.1.5 实现 to_dict() 序列化方法

- [x] 1.2 实现 SkillsLoader 类
  - [x] 1.2.1 实现 __init__() 方法（接受 base_path）
  - [x] 1.2.2 实现 scan() 方法（递归扫描 SKILL.md）
  - [x] 1.2.3 实现 _parse_skill_file() 方法（解析 frontmatter）
  - [x] 1.2.4 实现 get_skill() 方法（按名称查询）
  - [x] 1.2.5 实现 list_skills() 方法（列出所有 Skills）

- [x] 1.3 实现错误处理
  - [x] 1.3.1 YAML 解析错误时记录警告并跳过
  - [x] 1.3.2 缺少必需字段时记录警告并跳过
  - [x] 1.3.3 文件读取错误时记录警告并跳过

## Task 2: Capability_Registry 实现

- [x] 2.1 实现 CapabilityRegistry 类
  - [x] 2.1.1 实现 __init__() 方法（接受 SkillsLoader）
  - [x] 2.1.2 实现 register_handler() 方法
  - [x] 2.1.3 实现 register_state() 方法
  - [x] 2.1.4 实现 invoke_handler() 方法（支持 async）
  - [x] 2.1.5 实现 get_state() 方法（支持 async）

- [x] 2.2 实现元数据查询
  - [x] 2.2.1 实现 list_capabilities() 方法
  - [x] 2.2.2 实现 get_capability_metadata() 方法
  - [x] 2.2.3 实现 filter_by_task_type() 方法

- [x] 2.3 实现验证和错误处理
  - [x] 2.3.1 注册时验证 Skill 存在（警告但允许）
  - [x] 2.3.2 重复注册时抛出 ValueError
  - [x] 2.3.3 调用不存在的 handler 时抛出 ValueError
  - [x] 2.3.4 Handler 执行失败时包装异常

## Task 3: Knowledge_Injector 实现

- [x] 3.1 实现 KnowledgeInjector 类
  - [x] 3.1.1 实现 __init__() 方法（接受 SkillsLoader）
  - [x] 3.1.2 实现 get_skills_knowledge() 方法
  - [x] 3.1.3 实现 context_filter 支持
  - [x] 3.1.4 实现 get_all_skills_summary() 方法

- [x] 3.2 实现知识格式化
  - [x] 3.2.1 格式化为 Markdown 章节
  - [x] 3.2.2 包含 Skill 名称和描述
  - [x] 3.2.3 包含完整指令文本

## Task 4: OwlClaw 应用集成

- [x] 4.1 实现 OwlClaw 类
  - [x] 4.1.1 实现 __init__() 方法
  - [x] 4.1.2 实现 mount_skills() 方法
  - [x] 4.1.3 实现 @handler 装饰器
  - [x] 4.1.4 实现 @state 装饰器

- [x] 4.2 实现错误处理
  - [x] 4.2.1 mount_skills() 前使用装饰器时抛出错误
  - [x] 4.2.2 装饰器参数验证

## Task 5: 单元测试

- [x] 5.1 Skills_Loader 测试
  - [x] 5.1.1 测试 scan() 发现 SKILL.md 文件
  - [x] 5.1.2 测试解析有效 frontmatter
  - [x] 5.1.3 测试解析无效 YAML
  - [x] 5.1.4 测试缺少必需字段
  - [x] 5.1.5 测试懒加载机制
  - [x] 5.1.6 测试 references_dir 和 scripts_dir

- [x] 5.2 Capability_Registry 测试
  - [x] 5.2.1 测试 register_handler()
  - [x] 5.2.2 测试重复注册抛出错误
  - [x] 5.2.3 测试 invoke_handler() 成功
  - [x] 5.2.4 测试 invoke_handler() 未找到
  - [x] 5.2.5 测试 invoke_handler() 失败
  - [x] 5.2.6 测试 register_state()
  - [x] 5.2.7 测试 get_state()

- [x] 5.3 Knowledge_Injector 测试
  - [x] 5.3.1 测试 get_skills_knowledge()
  - [x] 5.3.2 测试 context_filter
  - [x] 5.3.3 测试空 Skills 列表
  - [x] 5.3.4 测试 get_all_skills_summary()

- [x] 5.4 OwlClaw 集成测试
  - [x] 5.4.1 测试 mount_skills() 和装饰器
  - [x] 5.4.2 测试端到端 Skill 加载和调用

## Task 6: 文档和示例

- [x] 6.1 创建示例 SKILL.md 文件
  - [x] 6.1.1 创建 examples/capabilities/entry-monitor/SKILL.md
  - [x] 6.1.2 创建 examples/capabilities/morning-decision/SKILL.md

- [x] 6.2 创建使用示例
  - [x] 6.2.1 创建 examples/basic_usage.py
  - [x] 6.2.2 添加注释说明

- [x] 6.3 更新 README
  - [x] 6.3.1 添加 Skills 挂载说明
  - [x] 6.3.2 添加装饰器使用说明

## Task 7: 集成到 OwlClaw 主包

- [x] 7.1 创建包结构
  - [x] 7.1.1 创建 owlclaw/capabilities/__init__.py
  - [x] 7.1.2 创建 owlclaw/capabilities/skills.py
  - [x] 7.1.3 创建 owlclaw/capabilities/registry.py
  - [x] 7.1.4 创建 owlclaw/capabilities/knowledge.py

- [x] 7.2 导出公共 API
  - [x] 7.2.1 在 owlclaw/__init__.py 中导出 OwlClaw
  - [x] 7.2.2 在 owlclaw/capabilities/__init__.py 中导出核心类

- [x] 7.3 添加依赖
  - [x] 7.3.1 在 pyproject.toml 中添加 pyyaml

## Task 8: 验收测试

- [x] 8.1 端到端测试
  - [x] 8.1.1 创建测试 capabilities 目录
  - [x] 8.1.2 测试 mount_skills() 扫描
  - [x] 8.1.3 测试 handler 注册和调用
  - [x] 8.1.4 测试 state 注册和查询
  - [x] 8.1.5 测试知识注入

- [x] 8.2 性能测试
  - [x] 8.2.1 测试 100 个 Skills 的加载时间
  - [x] 8.2.2 测试懒加载的内存占用
  - [x] 8.2.3 测试元数据查询性能

- [x] 8.3 错误场景测试
  - [x] 8.3.1 测试无效 YAML 的处理
  - [x] 8.3.2 测试缺少字段的处理
  - [x] 8.3.3 测试重复注册的处理

## Backlog

- [x] **R4 验收标准 4**：Run 结束后释放缓存的完整 Skill 内容（已在 `AgentRuntime.run()` 结束后调用缓存释放）

### 运行时增强（来自 OpenClaw 对标分析，2026-02-24）

- [ ] **Skill Prerequisites（加载前提条件）**：在 SKILL.md 的 `owlclaw` 字段中增加 `prerequisites`（env/bins/config/python_packages/os），加载时检查不满足则跳过该 Skill 并记录警告。参考 OpenClaw 的 `metadata.openclaw.requires`。
- [ ] **Session Skill Snapshot**：Agent Run 开始时快照当前可用 Skills 列表，Run 内保持稳定（不受文件系统变更影响）。Run 结束后刷新快照。参考 OpenClaw 的 session snapshot 机制。
- [ ] **Token Impact 估算**：KnowledgeInjector 注入 prompt 时计算 token 开销（per-skill 和总量），纳入 governance budget 控制。当总 token 超过阈值时自动按 focus 优先级裁剪。参考 OpenClaw 的 `formatSkillsForPrompt` 精确计算。
- [ ] **Skill 优先级/覆盖**：定义三层优先级（workspace > managed/installed > bundled），同名 Skill 高优先级覆盖低优先级。为 OwlHub 上线后的 Skill 冲突做准备。
- [ ] **Skill Enable/Disable 运行时控制**：支持在 owlclaw.yaml 中 `skills.entries.<name>.enabled: false` 禁用特定 Skill，不删除文件。参考 OpenClaw 的 `skills.entries` 配置。
- [ ] **Skill 环境变量注入生命周期**：Agent Run 开始时注入 Skill 声明的环境变量，Run 结束后恢复原始环境。参考 OpenClaw 的 per-run env injection。
- [ ] **Skills Watcher（热重载）**：监听 Skills 目录文件变更，自动刷新 Skills 列表（带 debounce）。已在 design.md 未来扩展中提及，提升为正式 backlog。
