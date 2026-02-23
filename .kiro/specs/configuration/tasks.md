# Configuration 系统实现任务

## 文档联动

- requirements: `.kiro/specs/configuration/requirements.md`
- design: `.kiro/specs/configuration/design.md`
- tasks: `.kiro/specs/configuration/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 任务列表

### Phase 1：核心配置框架

- [x] **Task 1**: 创建 `owlclaw/config/` 模块结构
  - 创建 `__init__.py`, `models.py`, `manager.py`, `loader.py`
  - 定义所有子配置的 Pydantic 模型（AgentConfig, GovernanceConfig, TriggersConfig, IntegrationsConfig, SecurityConfig, MemoryConfig）
  - 定义根配置 OwlClawConfig（继承 BaseSettings）
  - 所有字段设置合理的默认值、验证规则、Field 描述

- [x] **Task 2**: 实现 `YAMLConfigLoader`
  - YAML 文件查找逻辑（OWLCLAW_CONFIG env → --config CLI → ./owlclaw.yaml）
  - yaml.safe_load + 错误处理（行号、列号）
  - 空文件 / 不存在文件的优雅降级

- [x] **Task 3**: 实现 `ConfigManager` 单例
  - `load()`: 合并 defaults → YAML → env vars → overrides
  - `get()`: 返回当前配置
  - `on_change()`: 注册变更监听器
  - 线程安全（Lock 保护 _config 引用）

- [ ] **Task 4**: 实现环境变量映射
  - Pydantic BaseSettings 的 `env_prefix="OWLCLAW_"` + `env_nested_delimiter="__"`
  - 测试嵌套配置的环境变量映射
  - 文档化映射规则

- [ ] **Task 5**: 实现 `app.configure()` API
  - OwlClaw 类的 `configure(**kwargs)` 方法
  - 扁平化参数到嵌套字典的转换逻辑
  - 常用快捷参数映射（soul → agent.soul, model → integrations.llm.model）
  - 验证覆盖值的合法性

- [ ] **Task 6**: 创建默认 `owlclaw.yaml` 模板
  - 包含所有配置段的注释模板
  - 放置在 `templates/owlclaw.yaml`
  - CLI `owlclaw init` 命令生成到项目目录

### Phase 2：热更新与 CLI

- [ ] **Task 7**: 实现 `ConfigManager.reload()`
  - diff 算法：深度比较新旧配置
  - hot_reloadable 白名单过滤
  - cold_only 字段检测和跳过提示
  - 验证失败时回滚
  - 通知 listeners

- [ ] **Task 8**: 实现 `owlclaw reload` CLI 命令
  - Unix: 发送 SIGHUP 信号
  - Windows: HTTP POST /admin/reload
  - 输出 applied/skipped 报告
  - 错误处理和用户提示

- [ ] **Task 9**: 实现配置变更监听器
  - Governance 模块注册 listener → 重新加载预算/限流规则
  - Security 模块注册 listener → 重新加载 sanitizer/risk gate 规则
  - Agent Runtime 注册 listener → 热更新 Heartbeat 频率

### Phase 3：测试与文档

- [ ] **Task 10**: 单元测试
  - Pydantic 模型验证（默认值、边界条件、错误消息）
  - YAML 解析（正常、空、语法错误、类型错误）
  - 环境变量覆盖（各种嵌套级别）
  - 热更新 diff + 应用 + 回滚
  - app.configure() 覆盖链
  - 目标覆盖率：> 90%

- [ ] **Task 11**: 集成测试
  - ConfigManager 完整加载流程（YAML + env + overrides）
  - reload 端到端流程
  - listener 通知机制

- [ ] **Task 12**: 文档
  - owlclaw.yaml 完整配置参考（所有字段、类型、默认值、描述）
  - 环境变量映射表
  - 热更新支持矩阵
  - 配置最佳实践指南

