# 需求文档

## 简介

本文档定义了 OwlClaw 能力注册和 Skills 挂载系统的需求。这是 Agent 运行时的核心基础设施，负责从业务应用目录加载 Skills（遵循 Agent Skills 规范）、提供能力注册装饰器、以及将 Skills 知识文档注入到 Agent 的 system prompt 中。

该系统使业务应用能够以结构化、可发现的方式向 AI Agent 暴露其能力，同时保持业务知识（Skills）和业务逻辑（handlers）的分离。

## 术语表

- **Capability（能力）**: 可被 Agent 调用的业务功能，由 handler（Python 函数）和关联的知识文档（Skill）组成
- **Skill（技能）**: 遵循 Agent Skills 规范的知识文档（SKILL.md，包含 YAML frontmatter + Markdown 指令），描述何时以及如何使用某个能力
- **Handler（处理器）**: 用 @handler 装饰的 Python 函数，实现能力的执行逻辑
- **State（状态）**: 用 @state 装饰的 Python 函数，为 Agent 提供可查询的业务状态
- **Skills_Loader（技能加载器）**: 负责从应用目录发现和加载 SKILL.md 文件的组件
- **Capability_Registry（能力注册表）**: 管理 handlers 和 states 注册与查找的组件
- **Agent_Runtime（Agent 运行时）**: 使用已注册能力和 Skills 构建 Agent prompts 并执行 function calls 的组件
- **Frontmatter（前置元数据）**: SKILL.md 文件开头的 YAML 元数据，包含关于 Skill 的结构化信息
- **Progressive_Loading（渐进式加载）**: 启动时仅加载元数据、按需加载完整指令的策略，以最小化 token 使用

## 需求

### 需求 1：Skills 发现与加载

**用户故事：** 作为业务应用开发者，我希望 OwlClaw 能自动从我的应用 capabilities 目录发现并加载 Skills，这样我就不需要手动注册每个 Skill。

#### 验收标准

1. WHEN Skills_Loader 使用目录路径初始化时，THE System SHALL 递归扫描 SKILL.md 文件
2. WHEN 发现 SKILL.md 文件时，THE System SHALL 解析其 YAML frontmatter 以提取元数据
3. WHEN frontmatter 解析成功时，THE System SHALL 验证必需字段（name、description）是否存在
4. IF frontmatter 解析失败或缺少必需字段，THEN THE System SHALL 记录警告并跳过该 Skill
5. WHEN 所有 Skills 被发现后，THE System SHALL 返回 Skill 元数据对象的集合

### 需求 2：Agent Skills 规范合规性

**用户故事：** 作为开发者，我希望 OwlClaw 遵循 Agent Skills 开放规范，这样 Skills 可以在不同 Agent 系统间移植。

#### 验收标准

1. THE System SHALL 支持 Agent Skills 规范的 YAML frontmatter 字段（name、description、metadata）
2. THE System SHALL 支持 Skill 文件夹内的可选子目录（references/、scripts/、assets/）
3. WHEN 加载 Skill 时，THE System SHALL 保留 frontmatter 之后的 Markdown 内容作为指令文本
4. THE System SHALL 支持仅包含标准 Agent Skills 字段（不含 OwlClaw 扩展）的 Skills
5. WHEN Skill 仅使用标准字段时，THE System SHALL 成功加载而不出错

### 需求 3：OwlClaw 扩展字段

**用户故事：** 作为 OwlClaw 用户，我希望在 Skills 中指定 OwlClaw 特定的元数据，这样我可以配置任务路由、约束和触发器。

#### 验收标准

1. THE System SHALL 支持 SKILL.md frontmatter 中的可选 "owlclaw" 部分
2. WHEN owlclaw 部分包含 "task_type" 字段时，THE System SHALL 存储它用于 AI 路由
3. WHEN owlclaw 部分包含 "constraints" 对象时，THE System SHALL 存储它用于治理过滤
4. WHEN owlclaw 部分包含 "trigger" 字段时，THE System SHALL 存储它用于触发器关联
5. WHEN owlclaw 部分不存在时，THE System SHALL 对所有 OwlClaw 特定字段使用默认值

### 需求 4：渐进式加载策略

**用户故事：** 作为系统运维人员，我希望 Skills 能高效加载，这样 Agent 启动快速且 token 使用最小化。

#### 验收标准

1. WHEN System 启动时，THE Skills_Loader SHALL 仅加载 frontmatter 元数据（不加载完整指令文本）
2. WHEN Agent run 需要特定 Skill 时，THE System SHALL 按需加载完整指令文本
3. WHEN Skill 的完整内容被加载时，THE System SHALL 在 Agent run 期间缓存它
4. WHEN Agent run 完成时，THE System SHALL 释放缓存的完整 Skill 内容
5. THE System SHALL 跟踪内存中已加载的 Skills 并提供查询已加载 Skills 的方法

### 需求 5：能力 Handler 注册

**用户故事：** 作为业务应用开发者，我希望使用装饰器注册能力 handlers，这样我可以轻松地将业务逻辑连接到 Skills。

#### 验收标准

1. THE System SHALL 提供接受 Skill 名称参数的 @handler 装饰器
2. WHEN 函数被 @handler(name) 装饰时，THE Capability_Registry SHALL 将该函数注册为该 Skill 的 handler
3. WHEN handler 被注册时，THE System SHALL 验证给定名称的 Skill 是否存在
4. IF handler 名称对应的 Skill 不存在，THEN THE System SHALL 记录警告但允许注册
5. WHEN 为同一 Skill 名称注册多个 handlers 时，THE System SHALL 抛出错误

### 需求 6：状态提供者注册

**用户故事：** 作为业务应用开发者，我希望使用装饰器注册状态提供者，这样 Agents 可以查询业务状态。

#### 验收标准

1. THE System SHALL 提供接受状态名称参数的 @state 装饰器
2. WHEN 函数被 @state(name) 装饰时，THE Capability_Registry SHALL 将该函数注册为状态提供者
3. WHEN 状态提供者被注册时，THE System SHALL 验证函数是 async 或返回 dict
4. WHEN 为同一名称注册多个状态提供者时，THE System SHALL 抛出错误
5. THE System SHALL 提供按名称调用状态提供者并返回其结果的方法

### 需求 7：Skills 知识注入

**用户故事：** 作为 Agent 运行时，我希望将相关 Skills 知识注入到 system prompt 中，这样 Agent 能理解何时以及如何使用能力。

#### 验收标准

1. WHEN 构建 Agent prompt 时，THE System SHALL 提供检索指定 Skill 名称的 Skills 知识的方法
2. WHEN 请求 Skills 知识时，THE System SHALL 为指定 Skills 加载完整指令文本
3. WHEN 格式化 Skills 知识时，THE System SHALL 包含 Skill 名称、描述和指令文本
4. THE System SHALL 支持按上下文过滤 Skills（例如，交易时间内仅显示交易相关 Skills）
5. WHEN 没有 Skills 匹配过滤条件时，THE System SHALL 返回空知识部分

### 需求 8：能力元数据访问

**用户故事：** 作为治理层，我希望访问能力元数据，这样我可以基于约束和任务类型过滤能力。

#### 验收标准

1. THE Capability_Registry SHALL 提供列出所有已注册能力及其元数据的方法
2. WHEN 列出能力时，THE System SHALL 包含 Skill 名称、描述、task_type 和 constraints
3. THE System SHALL 提供按名称查询特定能力元数据的方法
4. WHEN 能力未找到时，THE System SHALL 返回 None 或抛出清晰的错误
5. THE System SHALL 提供按 task_type 过滤能力的方法

### 需求 9：Handler 调用

**用户故事：** 作为 Agent 运行时，我希望按名称调用能力 handlers，这样我可以执行 Agent function calls。

#### 验收标准

1. THE Capability_Registry SHALL 提供按 Skill 名称和参数调用 handler 的方法
2. WHEN 调用 handler 时，THE System SHALL 将提供的参数传递给 handler 函数
3. WHEN handler 执行成功时，THE System SHALL 返回 handler 的结果
4. IF handler 抛出异常，THEN THE System SHALL 传播异常并附带失败 handler 的上下文信息
5. WHEN Skill 名称没有注册 handler 时，THE System SHALL 抛出清晰的错误

### 需求 10：错误处理与验证

**用户故事：** 作为开发者，我希望在 Skills 或 handlers 配置错误时获得清晰的错误消息，这样我可以快速修复问题。

#### 验收标准

1. WHEN SKILL.md 文件有无效的 YAML frontmatter 时，THE System SHALL 记录文件路径和解析错误
2. WHEN Skill 缺少必需字段时，THE System SHALL 记录缺少哪些字段
3. WHEN handler 为不存在的 Skill 注册时，THE System SHALL 记录包含 Skill 名称的警告
4. WHEN 注册重复 handlers 时，THE System SHALL 抛出包含两个 handler 名称的错误
5. WHEN handler 调用失败时，THE System SHALL 在异常消息中包含 Skill 名称和原始错误

### 需求 11：Skills 目录结构支持

**用户故事：** 作为业务应用开发者，我希望在子目录中组织 Skills，这样我可以对相关能力进行分组。

#### 验收标准

1. THE Skills_Loader SHALL 支持 capabilities 目录内的嵌套目录结构
2. WHEN 扫描 Skills 时，THE System SHALL 发现任意深度的 SKILL.md 文件
3. WHEN Skill 文件夹包含 references/ 子目录时，THE System SHALL 使引用文件可访问
4. WHEN Skill 文件夹包含 scripts/ 子目录时，THE System SHALL 使脚本文件可访问
5. THE System SHALL 提供检索 Skill 的 references 或 scripts 文件路径的方法

### 需求 12：Skill 元数据序列化

**用户故事：** 作为开发者，我希望将 Skill 元数据序列化为 JSON，这样我可以检查已加载的 Skills 并调试问题。

#### 验收标准

1. THE System SHALL 提供将所有已加载 Skill 元数据导出为 JSON 的方法
2. WHEN 导出元数据时，THE System SHALL 包含 name、description、task_type、constraints 和文件路径
3. THE System SHALL 支持按名称导出单个 Skill 的元数据
4. WHEN 导出时，THE System SHALL 排除完整指令文本（仅元数据）
5. THE 导出的 JSON SHALL 是有效的且可被标准 JSON 库解析
