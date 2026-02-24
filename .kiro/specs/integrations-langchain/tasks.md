# 实现计划：LangChain 集成

## 文档联动

- requirements: `.kiro/specs/integrations-langchain/requirements.md`
- design: `.kiro/specs/integrations-langchain/design.md`
- tasks: `.kiro/specs/integrations-langchain/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

本实现计划将 LangChain 编排框架集成到 OwlClaw Agent 系统中。实现将遵循隔离设计模式，所有 LangChain 相关代码集中在 `owlclaw/integrations/langchain/` 目录中，提供 Runnable 注册、schema 验证、治理集成、可观测性追踪等功能。

实现采用增量方式，每个任务都建立在前一个任务的基础上，确保每一步都能验证核心功能。

## 任务列表

- [x] 1. 创建 LangChain 集成模块基础结构
  - 创建 `owlclaw/integrations/langchain/` 目录
  - 创建 `__init__.py` 文件，定义公开接口
  - 创建 `config.py` 文件，定义配置数据类
  - 创建 `errors.py` 文件，定义异常类型
  - 添加必要的导入和类型注解
  - 配置 setup.py/pyproject.toml 将 LangChain 定义为可选依赖
  - _需求：FR-1, FR-2_

- [x] 2. 实现配置管理
  - [x] 2.1 实现 LangChainConfig 数据类
    - 定义配置字段（enabled、version_check、timeout、tracing、privacy）
    - 实现 `from_yaml` 类方法加载 YAML 配置
    - 实现 `_replace_env_vars` 静态方法替换环境变量
    - 实现 `validate` 方法验证配置合法性
    - _需求：FR-19, FR-20_
  
  - [x]* 2.2 为配置加载编写单元测试
    - 测试从 YAML 加载配置
    - 测试环境变量替换
    - 测试配置验证（有效和无效配置）
    - _需求：FR-19, FR-20_

- [x] 3. 实现 SchemaBridge 组件
  - [x] 3.1 实现 Schema 验证和转换
    - 实现 `validate_input` 方法使用 jsonschema 验证输入
    - 实现 `transform_input` 方法转换输入数据
    - 实现 `transform_output` 方法转换输出数据
    - 定义 `ValidationError` 异常类
    - _需求：FR-5, FR-6_
  
  - [x]* 3.2 为 Schema 验证编写属性测试
    - **属性 3：输入 Schema 验证**
    - **验证需求：FR-5.1**
  
  - [x]* 3.3 为 Schema 验证失败编写属性测试
    - **属性 4：Schema 验证失败响应**
    - **验证需求：FR-5.3**
  
  - [x]* 3.4 为输出转换编写属性测试
    - **属性 5：输出格式封装**
    - **验证需求：FR-6.2**

- [x] 4. 实现 ErrorHandler 组件
  - [x] 4.1 实现异常映射和错误处理
    - 定义 `EXCEPTION_MAPPING` 异常映射表
    - 实现 `map_exception` 方法映射 LangChain 异常
    - 实现 `create_error_response` 方法创建错误响应
    - 实现 `handle_fallback` 方法处理 fallback
    - _需求：FR-16, FR-17_
  
  - [x]* 4.2 为异常捕获编写属性测试
    - **属性 10：异常捕获**
    - **验证需求：FR-16.1**
  
  - [x]* 4.3 为异常映射编写属性测试
    - **属性 11：异常映射**
    - **验证需求：FR-16.2**

- [x] 5. 检查点 - 确保基础组件测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. 实现 TraceManager 组件
  - [x] 6.1 实现 Trace 管理
    - 定义 `TraceSpan` 数据类
    - 实现 `TraceManager` 类
    - 实现 `create_span` 方法创建 trace span
    - 实现 `_create_langfuse_span` 方法集成 Langfuse
    - 实现 `_generate_trace_id` 方法生成 trace ID
    - _需求：FR-13, FR-14_
  
  - [x]* 6.2 为 Trace Span 创建编写属性测试
    - **属性 9：Trace Span 创建**
    - **验证需求：FR-13.1**

- [x] 7. 实现 LangChainAdapter 核心功能
  - [x] 7.1 实现 Adapter 初始化和注册
    - 定义 `RunnableConfig` 数据类
    - 实现 `LangChainAdapter` 类
    - 实现 `__init__` 方法初始化适配器
    - 实现 `register_runnable` 方法注册 Runnable
    - 实现 `_create_handler` 方法创建 capability handler
    - _需求：FR-3, FR-4_
  
  - [x]* 7.2 为 Runnable 类型验证编写属性测试
    - **属性 1：Runnable 类型验证**
    - **验证需求：FR-3.4**
  
  - [x]* 7.3 为注册失败编写属性测试
    - **属性 2：注册失败错误信息**
    - **验证需求：FR-3.5**

- [x] 8. 实现 Runnable 执行逻辑
  - [x] 8.1 实现 execute 方法
    - 实现输入 schema 验证
    - 实现输入转换
    - 实现 trace span 创建
    - 实现 Runnable 执行（带超时）
    - 实现错误处理和 fallback
    - 实现输出转换
    - 实现 span 结束
    - _需求：FR-5, FR-6, FR-7, FR-13, FR-16, FR-17_
  
  - [x] 8.2 实现 _execute_with_timeout 方法
    - 检测 Runnable 是否支持异步（ainvoke 方法）
    - 异步 Runnable 使用 ainvoke
    - 同步 Runnable 使用 run_in_executor
    - 应用超时控制
    - _需求：FR-7, FR-8_
  
  - [x]* 8.3 为异步检测编写属性测试
    - **属性 6：异步检测**
    - **验证需求：FR-7.1**

- [x] 9. 实现重试机制
  - [x] 9.1 实现重试策略
    - 定义 `RetryPolicy` 数据类
    - 实现 `calculate_backoff_delay` 函数计算重试延迟
    - 实现 `should_retry` 函数判断是否应该重试
    - 在 execute 方法中集成重试逻辑
    - _需求：FR-18_
  
  - [x]* 9.2 为指数退避编写属性测试
    - **属性 12：指数退避重试**
    - **验证需求：FR-18.4**

- [x] 10. 检查点 - 确保核心功能测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 11. 集成 Governance Layer
  - [x] 11.1 在 execute 方法中添加权限验证
    - 在执行前调用 Governance Layer 验证权限
    - 传递执行上下文（user_id、agent_id、capability_name）
    - 权限验证失败时返回 403 错误
    - 应用速率限制和配额控制
    - _需求：FR-9, FR-10_
  
  - [x]* 11.2 为权限验证失败编写属性测试
    - **属性 7：权限验证失败响应**
    - **验证需求：FR-9.3**
  
  - [x]* 11.3 编写 Governance 集成测试
    - 测试权限验证通过的情况
    - 测试权限验证失败的情况
    - 测试速率限制触发
    - _需求：FR-9, FR-10_

- [x] 12. 集成 Ledger
  - [x] 12.1 在 execute 方法中添加 Ledger 记录
    - 在执行开始时记录开始事件
    - 在执行结束时记录完成事件（成功或失败）
    - 记录执行时长、输入输出、错误信息
    - 记录 trace_id 和 span_id
    - _需求：FR-11, FR-12_
  
  - [x]* 12.2 为执行记录编写属性测试
    - **属性 8：执行记录完整性**
    - **验证需求：FR-11.1, FR-11.2**
  
  - [x]* 12.3 编写 Ledger 集成测试
    - 测试成功执行的记录
    - 测试失败执行的记录
    - 测试记录包含所有必需字段
    - _需求：FR-11, FR-12_

- [x] 13. 实现隐私保护
  - [x] 13.1 实现数据脱敏
    - 创建 `PrivacyMasker` 类
    - 定义 PII 检测模式（邮箱、电话）
    - 定义密钥检测模式（API key、password）
    - 实现 `mask_data` 方法递归脱敏数据
    - 在输入输出记录前应用脱敏
    - _需求：NFR-5_
  
  - [x]* 13.2 为 PII 脱敏编写属性测试
    - **属性 13：PII 脱敏**
    - **验证需求：NFR-5.2**
  
  - [x]* 13.3 编写隐私保护单元测试
    - 测试邮箱脱敏
    - 测试电话脱敏
    - 测试 API key 脱敏
    - 测试自定义模式脱敏
    - _需求：NFR-5_

- [x] 14. 实现 OwlClawApp 集成
  - [x] 14.1 在 OwlClawApp 中添加 LangChain 支持
    - 在 `OwlClawApp` 类中添加 `_langchain_adapter` 属性
    - 实现 `register_langchain_runnable` 方法
    - 实现装饰器支持（扩展 `@app.handler`）
    - 在应用初始化时加载 LangChain 配置
    - _需求：FR-3_
  
  - [x]* 14.2 编写集成测试
    - 测试注册 Runnable
    - 测试执行 Runnable
    - 测试装饰器注册
    - _需求：FR-3_

- [x] 15. 检查点 - 确保集成测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 16. 实现版本检查
  - [ ] 16.1 实现 LangChain 版本验证
    - 实现 `check_langchain_version` 函数
    - 在模块导入时检查 LangChain 版本
    - 版本不兼容时抛出清晰的错误
    - 提供版本升级建议
    - _需求：FR-2_
  
  - [ ]* 16.2 编写版本检查单元测试
    - 测试兼容版本通过
    - 测试不兼容版本被拒绝
    - 测试未安装 LangChain 的错误提示
    - _需求：FR-1, FR-2_

- [ ] 17. 实现流式输出支持
  - [ ] 17.1 实现流式执行
    - 检测 Runnable 是否支持 stream 方法
    - 实现 `execute_stream` 方法
    - 将流式输出转换为 OwlClaw 事件流
    - 处理流式输出中断
    - _需求：FR-8_
  
  - [ ]* 17.2 编写流式输出单元测试
    - 测试流式输出正常工作
    - 测试流式输出中断处理
    - 测试最终结果返回
    - _需求：FR-8_

- [ ] 18. 创建配置文件示例
  - [ ] 18.1 创建配置文件模板
    - 创建 `config/langchain.example.yaml` 示例配置
    - 包含开发环境配置
    - 包含生产环境配置
    - 包含禁用 LangChain 的配置
    - 添加详细的配置说明注释
    - _需求：FR-19_
  
  - [ ] 18.2 创建环境变量模板
    - 创建 `.env.example` 文件
    - 包含 LangChain 相关环境变量
    - 添加说明注释
    - _需求：FR-20_

- [ ] 19. 编写示例代码
  - [ ] 19.1 创建基础示例
    - 示例 1：注册简单 LLMChain
    - 示例 2：使用装饰器注册
    - 示例 3：配置 Fallback 和重试
    - 示例 4：自定义输入输出转换
    - 示例 5：与 Langfuse 集成
    - _需求：FR-21_
  
  - [ ]* 19.2 验证示例代码可运行
    - 在 CI 中运行所有示例
    - 验证示例输出符合预期
    - _需求：FR-21_

- [ ] 20. 编写端到端测试
  - [ ]* 20.1 编写完整流程测试
    - 创建真实的 LangChain Runnable
    - 注册并执行
    - 验证 Governance Layer 集成
    - 验证 Ledger 记录
    - 验证 Langfuse trace
    - _需求：所有功能需求_
  
  - [ ]* 20.2 编写错误场景测试
    - 测试 Schema 验证失败
    - 测试权限验证失败
    - 测试执行超时
    - 测试 Fallback 触发
    - 测试重试触发
    - _需求：FR-5, FR-9, FR-16, FR-17, FR-18_
  
  - [ ]* 20.3 编写性能测试
    - 测试 Schema 验证延迟
    - 测试输入输出转换延迟
    - 测试总适配层开销
    - 测试并发执行
    - _需求：NFR-1, NFR-2_

- [ ] 21. 编写文档
  - [ ] 21.1 编写 API 文档
    - 为所有公开类和方法添加文档字符串
    - 使用 Google 风格或 NumPy 风格
    - 包含参数说明、返回值说明和示例
    - _需求：FR-22_
  
  - [ ] 21.2 编写用户指南
    - 创建 `docs/integrations/langchain.md` 用户指南
    - 包含快速开始指南（< 5 分钟）
    - 包含配置说明
    - 包含错误处理指南
    - 包含最佳实践
    - 包含故障排查
    - _需求：FR-22_
  
  - [ ] 21.3 编写架构文档
    - 更新 `docs/ARCHITECTURE_ANALYSIS.md` 添加 LangChain 集成说明
    - 包含设计决策说明
    - 包含数据流图
    - 包含错误处理策略
    - 包含扩展点说明
    - _需求：FR-22_
  
  - [ ] 21.4 编写迁移指南
    - 创建从纯 LangChain 到 OwlClaw 的迁移指南
    - 包含常见迁移场景
    - 包含代码对比示例
    - 包含注意事项
    - _需求：FR-22_

- [ ] 22. 实现容错和降级
  - [ ] 22.1 实现降级逻辑
    - LangChain 未安装时的清晰错误提示
    - LangChain 初始化失败时的降级
    - Langfuse 不可用时的降级
    - 所有异常都被捕获并记录
    - _需求：NFR-3_
  
  - [ ]* 22.2 编写容错测试
    - 测试 LangChain 未安装
    - 测试 LangChain 初始化失败
    - 测试 Langfuse 不可用
    - 验证系统继续运行
    - _需求：NFR-3_

- [ ] 23. 实现健康检查
  - [ ] 23.1 实现健康检查端点
    - 检查 LangChain 是否可用
    - 检查 Langfuse 是否可用
    - 检查配置是否有效
    - 返回健康状态和详情
    - _需求：NFR-3_
  
  - [ ]* 23.2 编写健康检查测试
    - 测试健康状态正常
    - 测试健康状态异常
    - _需求：NFR-3_

- [ ] 24. 实现监控指标
  - [ ] 24.1 实现指标收集
    - 收集执行次数（按 capability 分组）
    - 收集执行成功率
    - 收集执行延迟（P50/P95/P99）
    - 收集错误率（按错误类型分组）
    - 收集 Fallback 使用率
    - 收集重试次数
    - _需求：NFR-1, NFR-2_
  
  - [ ] 24.2 实现指标导出
    - 支持 Prometheus 格式导出
    - 支持 JSON 格式导出
    - 提供查询接口
    - _需求：NFR-1, NFR-2_

- [ ] 25. 最终检查点 - 确保所有测试通过
  - 运行所有单元测试
  - 运行所有属性测试
  - 运行所有集成测试
  - 运行所有端到端测试
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
- 每个属性测试运行至少 100 次迭代

## 依赖关系

```
1. 基础结构
   ↓
2. 配置管理
   ↓
3. SchemaBridge ←─┐
   ↓              │
4. ErrorHandler   │
   ↓              │
5. 检查点 1       │
   ↓              │
6. TraceManager   │
   ↓              │
7. LangChainAdapter (依赖 3, 4, 6)
   ↓
8. Runnable 执行
   ↓
9. 重试机制
   ↓
10. 检查点 2
    ↓
11. Governance 集成
    ↓
12. Ledger 集成
    ↓
13. 隐私保护
    ↓
14. OwlClawApp 集成
    ↓
15. 检查点 3
    ↓
16-24. 其他功能和测试
    ↓
25. 最终检查点
```

## 预估工作量

- **Phase 1：基础组件**（任务 1-5）：1-2 天
- **Phase 2：核心功能**（任务 6-10）：1-2 天
- **Phase 3：集成**（任务 11-15）：1 天
- **Phase 4：完善功能**（任务 16-20）：1 天
- **Phase 5：文档和测试**（任务 21-25）：1-2 天

**总计**：4-6 天

## 验收标准

### 功能验收

- [ ] 可以通过 `pip install owlclaw[langchain]` 安装
- [ ] 可以注册 LangChain Runnable 为 capability
- [ ] 可以调用注册的 Runnable
- [ ] 输入 schema 验证正常工作
- [ ] 输入输出转换正常工作
- [ ] 执行记录到 Ledger
- [ ] 执行受 Governance Layer 约束
- [ ] 支持错误处理和 fallback
- [ ] 支持重试机制
- [ ] 支持与 Langfuse 集成

### 性能验收

- [ ] Schema 验证延迟 < 10ms (P95)
- [ ] 输入输出转换延迟 < 5ms (P95)
- [ ] 总适配层开销 < 20ms (P95)
- [ ] 支持每秒 100+ 次执行
- [ ] 支持 10+ 个并发执行

### 质量验收

- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 所有属性测试通过（每个至少 100 次迭代）
- [ ] 类型检查通过（mypy）
- [ ] 代码检查通过（ruff）
- [ ] 文档完整（API 文档、用户指南、架构文档）

### 文档验收

- [ ] API 文档完整（所有公开接口有文档字符串）
- [ ] 用户指南完整（快速开始、配置、最佳实践、故障排查）
- [ ] 架构文档完整（设计决策、数据流、错误处理）
- [ ] 示例代码完整（至少 5 个典型场景）
- [ ] 迁移指南完整

---

**维护者**：平台研发  
**最后更新**：2025-01-15
