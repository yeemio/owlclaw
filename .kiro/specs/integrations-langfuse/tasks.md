# 实现计划：Langfuse 集成

## 文档联动

- requirements: `.kiro/specs/integrations-langfuse/requirements.md`
- design: `.kiro/specs/integrations-langfuse/design.md`
- tasks: `.kiro/specs/integrations-langfuse/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

本实现计划将 Langfuse 可观测性集成到 OwlClaw Agent 系统中。实现将遵循隔离设计模式，所有 Langfuse 相关代码集中在 `owlclaw/integrations/langfuse.py` 中，提供 LLM 调用追踪、成本分析和性能监控能力。

实现采用增量方式，每个任务都建立在前一个任务的基础上，确保每一步都能验证核心功能。

## 任务列表

- [ ] 1. 创建 Langfuse 集成模块基础结构
  - 创建 `owlclaw/integrations/langfuse.py` 文件
  - 定义配置数据类 `LangfuseConfig`
  - 定义元数据数据类 `TraceMetadata`, `LLMSpanData`, `ToolSpanData`
  - 定义枚举类型 `SpanType`
  - 添加必要的导入和类型注解
  - _需求：FR-1, FR-2, FR-3, FR-13_

- [ ] 2. 实现 LangfuseClient 核心功能
  - [ ] 2.1 实现 LangfuseClient 初始化和连接管理
    - 实现 `__init__` 方法，接收 `LangfuseConfig`
    - 实现 `_initialize_client` 方法，初始化 Langfuse SDK 客户端
    - 实现降级逻辑：初始化失败时禁用客户端
    - 实现 `_should_sample` 方法，根据采样率决定是否创建 trace
    - _需求：FR-4.5, FR-13.1, FR-13.2, FR-13.3, FR-13.4_
  
  - [ ]* 2.2 为 LangfuseClient 初始化编写属性测试
    - **属性 14：配置验证**
    - **验证需求：FR-13.2**
  
  - [ ]* 2.3 为采样率编写属性测试
    - **属性 15：采样率遵守**
    - **验证需求：FR-13.4**

- [ ] 3. 实现 Trace 创建和管理
  - [ ] 3.1 实现 `create_trace` 方法
    - 接收 trace 名称、元数据和标签
    - 调用 Langfuse SDK 创建 trace
    - 处理异常并降级（返回 None）
    - 返回 trace_id
    - _需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4_
  
  - [ ] 3.2 实现 `end_trace` 方法
    - 接收 trace_id、输出和元数据
    - 调用 Langfuse SDK 结束 trace
    - 处理异常并记录警告
    - _需求：FR-4.2_
  
  - [ ] 3.3 实现 `flush` 方法
    - 刷新所有待上报的数据
    - 处理异常并记录警告
    - _需求：NFR-4.1_
  
  - [ ]* 3.4 为 Trace 创建编写属性测试
    - **属性 1：Trace 创建和内容完整性**
    - **验证需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4**
  
  - [ ]* 3.5 为 Trace 生命周期编写属性测试
    - **属性 7：Trace 生命周期管理**
    - **验证需求：FR-4.2**
  
  - [ ]* 3.6 为数据完整性编写属性测试
    - **属性 21：数据完整性保证**
    - **验证需求：NFR-4.1**

- [ ] 4. 实现 TokenCalculator 模块
  - [ ] 4.1 实现 TokenCalculator 类
    - 定义 `MODEL_PRICING` 定价表（包含 GPT-4、GPT-3.5、Claude 等模型）
    - 实现 `_normalize_model_name` 方法，标准化模型名称
    - 实现 `calculate_cost` 方法，根据 token 使用量和模型计算成本
    - 实现 `extract_tokens_from_response` 方法，从 LLM 响应中提取 token 数量
    - _需求：FR-6, FR-7_
  
  - [ ]* 4.2 为 Token 提取编写属性测试
    - **属性 11：Token 提取正确性**
    - **验证需求：FR-6.1, FR-6.3**
  
  - [ ]* 4.3 为成本计算编写属性测试
    - **属性 12：成本计算正确性**
    - **验证需求：FR-7.2**
  
  - [ ]* 4.4 为成本聚合编写属性测试
    - **属性 13：成本聚合正确性**
    - **验证需求：FR-8.1**

- [ ] 5. 检查点 - 确保基础功能测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 6. 实现 LLM Span 创建
  - [ ] 6.1 实现 `create_llm_span` 方法
    - 接收 trace_id、span 名称、LLM span 数据和父 span_id
    - 应用隐私脱敏（如果启用）
    - 调用 Langfuse SDK 创建 generation span
    - 包含 token 使用量、成本、延迟和状态
    - 处理异常并降级（返回 None）
    - 返回 span_id
    - _需求：FR-2.1, FR-2.2, FR-2.3, FR-2.4_
  
  - [ ]* 6.2 为 LLM Span 创建编写属性测试
    - **属性 3：LLM Span 创建和内容完整性**
    - **验证需求：FR-2.1, FR-2.2, FR-2.3, FR-2.4**
  
  - [ ]* 6.3 为 LLM 错误处理编写属性测试
    - **属性 4：LLM 错误处理**
    - **验证需求：FR-2.5**

- [ ] 7. 实现 Tool Span 创建
  - [ ] 7.1 实现 `create_tool_span` 方法
    - 接收 trace_id、span 名称、tool span 数据和父 span_id
    - 应用隐私脱敏（如果启用）
    - 调用 Langfuse SDK 创建 span
    - 包含工具名称、参数、结果、执行时长和状态
    - 处理异常并降级（返回 None）
    - 返回 span_id
    - _需求：FR-3.1, FR-3.2, FR-3.3, FR-3.4_
  
  - [ ]* 7.2 为 Tool Span 创建编写属性测试
    - **属性 5：Tool Span 创建和内容完整性**
    - **验证需求：FR-3.1, FR-3.2, FR-3.3, FR-3.4**
  
  - [ ]* 7.3 为 Tool 错误处理编写属性测试
    - **属性 6：Tool 错误处理**
    - **验证需求：FR-3.5**
  
  - [ ]* 7.4 为 Trace 嵌套结构编写属性测试
    - **属性 2：Trace 嵌套结构**
    - **验证需求：FR-1.5**

- [ ] 8. 实现 TraceContext 上下文管理
  - [ ] 8.1 实现 TraceContext 数据类和上下文管理
    - 定义 `TraceContext` 数据类（trace_id、parent_span_id、metadata）
    - 使用 `contextvars` 定义 `_trace_context` 上下文变量
    - 实现 `get_current` 类方法，获取当前上下文
    - 实现 `set_current` 类方法，设置当前上下文
    - 实现 `with_parent_span` 方法，创建带有父 span 的新上下文
    - _需求：FR-5.1, FR-5.2, FR-5.3, FR-5.4_
  
  - [ ]* 8.2 为 Context 传递编写属性测试
    - **属性 8：Context 在决策循环中传递**
    - **属性 9：Context 在 LLM 调用中可访问**
    - **属性 10：Context 在工具执行中可访问**
    - **验证需求：FR-5.1, FR-5.2, FR-5.3**

- [ ] 9. 实现 PrivacyMasker 隐私脱敏
  - [ ] 9.1 实现 PrivacyMasker 类
    - 定义 `PII_PATTERNS` 字典（邮箱、电话、SSN、信用卡）
    - 定义 `SECRET_PATTERNS` 字典（API key、Bearer token、密码）
    - 实现 `mask` 类方法，递归脱敏数据（字符串、字典、列表）
    - 实现 `_mask_string` 类方法，应用脱敏规则到字符串
    - 支持自定义脱敏规则（正则表达式）
    - _需求：FR-14.1, FR-14.2, FR-14.3, FR-14.4, FR-14.5_
  
  - [ ]* 9.2 为 PII 脱敏编写属性测试
    - **属性 16：PII 脱敏**
    - **验证需求：FR-14.2**
  
  - [ ]* 9.3 为密钥脱敏编写属性测试
    - **属性 17：密钥脱敏**
    - **验证需求：FR-14.3**
  
  - [ ]* 9.4 为自定义脱敏规则编写属性测试
    - **属性 18：自定义脱敏规则**
    - **验证需求：FR-14.4**
  
  - [ ]* 9.5 为脱敏结构保留编写属性测试
    - **属性 19：脱敏结构保留**
    - **验证需求：FR-14.5**

- [ ] 10. 检查点 - 确保核心模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 11. 集成到 Agent Runtime
  - [ ] 11.1 修改 AgentRuntime 以支持 Langfuse 追踪
    - 在 `owlclaw/agent/runtime/runtime.py` 中导入 Langfuse 模块
    - 在 `__init__` 方法中初始化 `LangfuseClient`
    - 在 `run` 方法开始时创建 trace
    - 设置 `TraceContext` 到当前上下文
    - 在 `run` 方法结束时结束 trace（包含总成本、总时长等元数据）
    - 在 finally 块中清理上下文并 flush 数据
    - 处理异常情况（记录错误到 trace）
    - _需求：FR-4.1, FR-4.2_
  
  - [ ]* 11.2 为 Agent Runtime 集成编写单元测试
    - 测试 trace 自动创建
    - 测试 trace 自动结束
    - 测试异常情况下的 trace 记录
    - _需求：FR-4.1, FR-4.2_

- [ ] 12. 集成到 LLM 客户端
  - [ ] 12.1 修改 LLMClient 以支持 LLM 调用追踪
    - 在 `owlclaw/integrations/llm.py` 中导入 Langfuse 模块
    - 在 `complete` 方法中获取当前 `TraceContext`
    - 记录 LLM 调用开始时间
    - 调用 LLM 并捕获响应
    - 提取 token 使用量并计算成本
    - 创建 LLM span（包含 prompt、response、tokens、cost、latency）
    - 处理 LLM 调用失败情况（创建失败的 span）
    - _需求：FR-2, FR-5.2, FR-6, FR-7_
  
  - [ ]* 12.2 为 LLM 客户端集成编写单元测试
    - 测试成功的 LLM 调用追踪
    - 测试失败的 LLM 调用追踪
    - 测试 token 和成本记录
    - _需求：FR-2, FR-6, FR-7_

- [ ] 13. 集成到工具执行系统
  - [ ] 13.1 修改 ToolExecutor 以支持工具调用追踪
    - 在 `owlclaw/agent/tools.py` 中导入 Langfuse 模块
    - 在 `execute` 方法中获取当前 `TraceContext`
    - 记录工具执行开始时间
    - 执行工具并捕获结果
    - 创建 tool span（包含 tool_name、arguments、result、duration）
    - 处理工具执行失败情况（创建失败的 span）
    - _需求：FR-3, FR-5.3_
  
  - [ ]* 13.2 为工具执行系统集成编写单元测试
    - 测试成功的工具调用追踪
    - 测试失败的工具调用追踪
    - 测试执行时长记录
    - _需求：FR-3_

- [ ] 14. 实现配置管理
  - [ ] 14.1 实现配置加载和验证
    - 创建 `load_langfuse_config` 函数，从 YAML 配置文件加载配置
    - 实现 `_replace_env_vars` 函数，替换配置中的环境变量（${VAR_NAME} 格式）
    - 实现 `validate_config` 函数，验证配置的合法性
    - 验证必需字段（public_key、secret_key）
    - 验证数值范围（sampling_rate、batch_size、flush_interval_seconds）
    - 验证自定义脱敏规则（正则表达式）
    - _需求：FR-13.1, FR-13.2_
  
  - [ ]* 14.2 为配置验证编写单元测试
    - 测试有效配置加载
    - 测试无效配置检测（缺少必需字段、无效数值范围）
    - 测试环境变量替换
    - 测试自定义脱敏规则验证
    - _需求：FR-13.1, FR-13.2_

- [ ] 15. 实现错误处理和降级逻辑
  - [ ] 15.1 完善所有错误处理场景
    - 确保 Langfuse 不可用时降级运行（不影响 Agent Run）
    - 确保所有异常都被捕获并记录警告日志
    - 确保 API key 不出现在日志中
    - 实现进程退出时的清理逻辑（使用 atexit）
    - _需求：NFR-3, NFR-5.3_
  
  - [ ]* 15.2 为容错降级编写属性测试
    - **属性 20：容错降级**
    - **验证需求：NFR-3.1, NFR-3.2, NFR-3.3**
  
  - [ ]* 15.3 为日志安全编写属性测试
    - **属性 22：日志安全**
    - **验证需求：NFR-5.3**

- [ ] 16. 检查点 - 确保集成测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 17. 创建配置文件示例
  - [ ] 17.1 创建配置文件模板
    - 创建 `config/langfuse.example.yaml` 示例配置文件
    - 包含开发环境配置示例
    - 包含生产环境配置示例
    - 包含禁用 Langfuse 的配置示例
    - 添加详细的配置说明注释
    - _需求：FR-13_
  
  - [ ] 17.2 创建环境变量模板
    - 创建 `.env.example` 文件
    - 包含 Langfuse 认证环境变量
    - 包含可选的自托管地址环境变量
    - _需求：FR-13, NFR-5.1_

- [ ] 18. 编写端到端集成测试
  - [ ]* 18.1 编写完整的 Agent Run 追踪测试
    - 创建完整的 Agent Run 场景
    - 验证 trace 创建
    - 验证 LLM span 创建
    - 验证 tool span 创建
    - 验证 trace 结束
    - 验证成本和时长聚合
    - _需求：FR-1, FR-2, FR-3, FR-4_
  
  - [ ]* 18.2 编写隐私脱敏端到端测试
    - 创建包含敏感信息的 Agent Run
    - 验证 PII 被正确脱敏
    - 验证密钥被正确脱敏
    - 验证数据结构被保留
    - _需求：FR-14_
  
  - [ ]* 18.3 编写错误场景端到端测试
    - 测试 Langfuse 不可用场景
    - 测试 LLM 调用失败场景
    - 测试工具执行失败场景
    - 验证系统继续正常运行
    - _需求：NFR-3_

- [ ] 19. 编写文档
  - [ ] 19.1 编写 API 文档
    - 为所有公开类和方法添加文档字符串
    - 包含参数说明、返回值说明和示例
    - 使用 Google 风格或 NumPy 风格的文档字符串
    - _需求：所有功能需求_
  
  - [ ] 19.2 编写用户指南
    - 创建 `docs/integrations/langfuse.md` 用户指南
    - 包含快速开始指南
    - 包含配置说明
    - 包含隐私保护指南
    - 包含故障排查指南
    - _需求：所有功能需求_
  
  - [ ] 19.3 编写架构文档
    - 更新 `docs/ARCHITECTURE_ANALYSIS.md` 添加 Langfuse 集成说明
    - 包含设计决策说明
    - 包含数据流图
    - 包含错误处理策略
    - _需求：所有功能需求_

- [ ] 20. 最终检查点 - 确保所有测试通过
  - 运行所有单元测试
  - 运行所有属性测试
  - 运行所有集成测试
  - 检查测试覆盖率（目标 ≥ 80%）
  - 运行类型检查（mypy）
  - 运行代码格式检查（ruff）
  - 如有问题请询问用户

## 注意事项

- 标记为 `*` 的任务是测试重点标记，不代表可跳过；发布前需完成并通过验收
- 每个任务都引用了具体的需求，便于追溯
- 检查点任务确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
- 所有代码使用 Python 3.8+ 和类型注解
- 遵循 PEP 8 代码风格
- 使用 pytest 作为测试框架
- 使用 hypothesis 作为属性测试框架

