# 任务清单

## Task 0: 契约与文档

- [ ] 0.1 确认 requirements.md 完整且与架构文档一致
- [ ] 0.2 确认 design.md 完整且包含所有组件设计
- [ ] 0.3 确认 tasks.md 覆盖所有需求的实现

## Task 1: LLMConfig 实现

- [x] 1.1 实现配置数据类
  - [x] 1.1.1 定义 ModelConfig 类
  - [x] 1.1.2 定义 TaskTypeRouting 类
  - [x] 1.1.3 定义 LLMConfig 类
  - [x] 1.1.4 使用 Pydantic 进行类型验证

- [x] 1.2 实现配置加载
  - [x] 1.2.1 实现 from_yaml() 类方法
  - [x] 1.2.2 实现环境变量替换（_substitute_env_dict）
  - [x] 1.2.3 实现配置验证
  - [x] 1.2.4 default_for_owlclaw() 最小默认配置

## Task 2: LLMClient 核心实现

- [x] 2.1 实现 LLMResponse 类
  - [x] 2.1.1 定义响应数据结构
  - [x] 2.1.2 实现 token 和成本计算

- [x] 2.2 实现 LLMClient 类
  - [x] 2.2.1 实现 __init__() 方法
  - [x] 2.2.2 实现 complete() 方法
  - [x] 2.2.3 实现 _route_model() 方法
  - [x] 2.2.4 实现 _call_with_fallback() 方法
  - [x] 2.2.5 实现 _parse_response() 方法

- [x] 2.3 实现 Function Calling 支持
  - [x] 2.3.1 支持 tools 参数传递
  - [x] 2.3.2 解析 function calls 响应
  - [x] 2.3.3 支持多个 function calls

## Task 3: 辅助组件实现

- [ ] 3.1 实现 PromptBuilder 类
  - [ ] 3.1.1 实现 build_system_message()
  - [ ] 3.1.2 实现 build_user_message()
  - [ ] 3.1.3 实现 build_function_result_message()

- [ ] 3.2 实现 ToolsConverter 类
  - [ ] 3.2.1 实现 capabilities_to_tools()
  - [ ] 3.2.2 处理参数 schema 转换

- [ ] 3.3 实现 TokenEstimator 类
  - [ ] 3.3.1 实现 estimate_tokens()
  - [ ] 3.3.2 实现 check_context_window()
  - [ ] 3.3.3 集成 tiktoken 库

## Task 4: 模型路由和降级

- [ ] 4.1 实现 task_type 路由
  - [ ] 4.1.1 根据 task_type 选择模型
  - [ ] 4.1.2 应用 task_type 特定的参数

- [ ] 4.2 实现模型降级链
  - [ ] 4.2.1 主模型失败时尝试 fallback
  - [ ] 4.2.2 记录降级日志
  - [ ] 4.2.3 所有模型失败时抛出异常

- [ ] 4.3 实现重试策略
  - [ ] 4.3.1 Rate limit 错误自动重试
  - [ ] 4.3.2 配置重试次数和延迟
  - [ ] 4.3.3 区分可重试和不可重试错误

## Task 5: Langfuse 集成

- [ ] 5.1 实现 Langfuse 初始化
  - [ ] 5.1.1 从配置读取 Langfuse 参数
  - [ ] 5.1.2 创建 Langfuse 客户端

- [ ] 5.2 实现 Trace 记录
  - [ ] 5.2.1 为每次 LLM 调用创建 trace
  - [ ] 5.2.2 记录 input、output、tokens、cost
  - [ ] 5.2.3 记录 function calls

- [ ] 5.3 实现错误追踪
  - [ ] 5.3.1 记录失败的调用
  - [ ] 5.3.2 记录降级事件

## Task 6: 错误处理

- [ ] 6.1 实现错误类型定义
  - [ ] 6.1.1 定义 AuthenticationError
  - [ ] 6.1.2 定义 RateLimitError
  - [ ] 6.1.3 定义 ContextWindowExceededError
  - [ ] 6.1.4 定义 ServiceUnavailableError

- [ ] 6.2 实现错误处理逻辑
  - [ ] 6.2.1 捕获 litellm 异常
  - [ ] 6.2.2 包装为 OwlClaw 异常
  - [ ] 6.2.3 记录详细错误信息

## Task 7: Mock 模式

- [ ] 7.1 实现 Mock 模式
  - [ ] 7.1.1 检测 mock_mode 配置
  - [ ] 7.1.2 返回预定义响应
  - [ ] 7.1.3 模拟 token 使用量

- [ ] 7.2 实现 Mock 响应配置
  - [ ] 7.2.1 支持文本响应
  - [ ] 7.2.2 支持 function call 响应

## Task 8: 单元测试

- [ ] 8.1 LLMConfig 测试
  - [ ] 8.1.1 测试 from_yaml() 加载配置
  - [ ] 8.1.2 测试环境变量替换
  - [ ] 8.1.3 测试配置验证

- [ ] 8.2 LLMClient 测试
  - [ ] 8.2.1 测试模型路由
  - [ ] 8.2.2 测试 function calling
  - [ ] 8.2.3 测试响应解析

- [ ] 8.3 辅助组件测试
  - [ ] 8.3.1 测试 PromptBuilder
  - [ ] 8.3.2 测试 ToolsConverter
  - [ ] 8.3.3 测试 TokenEstimator

- [ ] 8.4 错误处理测试
  - [ ] 8.4.1 测试认证错误
  - [ ] 8.4.2 测试 rate limit 重试
  - [ ] 8.4.3 测试模型降级

## Task 9: 集成测试

- [ ] 9.1 真实 API 调用测试
  - [ ] 9.1.1 测试 OpenAI 调用
  - [ ] 9.1.2 测试 Anthropic 调用
  - [ ] 9.1.3 测试 function calling

- [ ] 9.2 Langfuse 集成测试
  - [ ] 9.2.1 测试 trace 创建
  - [ ] 9.2.2 测试数据记录

- [ ] 9.3 模型降级测试
  - [ ] 9.3.1 模拟主模型失败
  - [ ] 9.3.2 验证 fallback 执行

## Task 10: 文档和示例

- [ ] 10.1 创建配置示例
  - [ ] 10.1.1 创建 owlclaw.yaml 示例
  - [ ] 10.1.2 添加配置说明注释

- [ ] 10.2 创建使用示例
  - [ ] 10.2.1 创建基本调用示例
  - [ ] 10.2.2 创建 function calling 示例
  - [ ] 10.2.3 创建模型路由示例

- [ ] 10.3 更新 README
  - [ ] 10.3.1 添加 LLM 集成说明
  - [ ] 10.3.2 添加配置参考

## Task 11: 集成到 OwlClaw 主包

- [x] 11.1 创建包结构
  - [x] 11.1.1 创建 owlclaw/integrations/llm.py

- [x] 11.2 导出公共 API
  - [x] 11.2.1 在 owlclaw/integrations/__init__.py 中导出 acompletion、LLMClient、LLMConfig、LLMResponse

- [ ] 11.3 添加依赖
  - [ ] 11.3.1 在 pyproject.toml 中添加 litellm
  - [ ] 11.3.2 在 pyproject.toml 中添加 tiktoken
  - [ ] 11.3.3 在 pyproject.toml 中添加 langfuse（可选）

## Task 12: 验收测试

- [ ] 12.1 功能验收
  - [ ] 12.1.1 验证所有需求的实现
  - [ ] 12.1.2 验证错误处理
  - [ ] 12.1.3 验证配置管理

- [ ] 12.2 性能验收
  - [ ] 12.2.1 测试调用延迟
  - [ ] 12.2.2 测试并发调用

- [ ] 12.3 成本验收
  - [ ] 12.3.1 验证成本计算准确性
  - [ ] 12.3.2 验证成本追踪

