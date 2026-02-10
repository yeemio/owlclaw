# 需求文档

## 简介

本文档定义 OwlClaw 与 litellm 的集成需求。litellm 为 OwlClaw 提供统一的 LLM 调用接口，支持 100+ 模型（OpenAI、Anthropic、Google、Azure 等），并提供模型降级、重试、成本追踪等能力。

## 术语表

- **litellm**: 开源的 LLM 统一接口库，支持 100+ 模型提供商
- **LLM_Client**: OwlClaw 对 litellm 的封装客户端
- **Function_Calling**: LLM 的函数调用能力，Agent 通过此能力选择执行哪个 capability
- **Model_Router**: 根据 task_type 路由到不同模型的组件
- **Fallback_Chain**: 模型降级链，主模型失败时自动切换到备用模型
- **Token_Tracking**: Token 使用量和成本追踪
- **Streaming**: 流式响应，逐步返回 LLM 输出
- **Context_Window**: 模型的上下文窗口大小限制
- **System_Prompt**: Agent 的系统提示词（身份、记忆、知识）
- **Temperature**: 模型的随机性参数（0-1）
- **Max_Tokens**: 单次调用的最大输出 token 数

## 需求

### 需求 1：LLM 客户端初始化和配置管理

**用户故事：** 作为 OwlClaw 开发者，我希望能够初始化 LLM 客户端并管理模型配置，以便 Agent 能够调用 LLM。

#### 验收标准

1. WHEN OwlClaw 启动时，THE LLM_Client SHALL 从配置文件读取模型配置
2. WHEN 配置包含 API keys 时，THE LLM_Client SHALL 从环境变量读取敏感信息
3. WHEN 配置包含多个模型时，THE LLM_Client SHALL 支持按 task_type 路由
4. WHEN 配置包含 fallback 模型时，THE LLM_Client SHALL 构建降级链
5. WHEN 配置无效时，THE LLM_Client SHALL 抛出清晰的配置错误

### 需求 2：Function Calling 支持

**用户故事：** 作为 Agent 运行时，我希望能够通过 function calling 让 LLM 选择执行哪个 capability，以便实现 Agent 自主决策。

#### 验收标准

1. THE LLM_Client SHALL 支持将 capabilities 转换为 function calling 的 tools 格式
2. WHEN 调用 LLM 时，THE LLM_Client SHALL 传递 tools 列表
3. WHEN LLM 返回 function call 时，THE LLM_Client SHALL 解析 function name 和 arguments
4. WHEN LLM 返回多个 function calls 时，THE LLM_Client SHALL 支持并行或顺序执行
5. WHEN LLM 不返回 function call 时，THE LLM_Client SHALL 返回文本响应

### 需求 3：模型路由（task_type → 模型）

**用户故事：** 作为治理层，我希望能够根据 task_type 路由到不同的模型，以便优化成本和质量。

#### 验收标准

1. THE LLM_Client SHALL 支持配置 task_type 到模型的映射
2. WHEN Agent run 指定 task_type 时，THE LLM_Client SHALL 使用对应的模型
3. WHEN task_type 没有配置映射时，THE LLM_Client SHALL 使用默认模型
4. THE LLM_Client SHALL 支持为不同 task_type 配置不同的 temperature 和 max_tokens
5. THE LLM_Client SHALL 记录每次调用使用的模型和 task_type

### 需求 4：模型降级和重试

**用户故事：** 作为 OwlClaw 运维者，我希望 LLM 调用失败时能够自动降级到备用模型，以便提高系统可用性。

#### 验收标准

1. THE LLM_Client SHALL 支持配置 fallback 模型链
2. WHEN 主模型调用失败时，THE LLM_Client SHALL 自动尝试 fallback 模型
3. WHEN 所有模型都失败时，THE LLM_Client SHALL 抛出异常并记录详细错误
4. THE LLM_Client SHALL 支持配置重试次数和延迟策略
5. THE LLM_Client SHALL 区分可重试错误（rate limit）和不可重试错误（invalid request）

### 需求 5：Token 使用量和成本追踪

**用户故事：** 作为 OwlClaw 运维者，我希望能够追踪 LLM 的 token 使用量和成本，以便控制预算。

#### 验收标准

1. THE LLM_Client SHALL 记录每次调用的 prompt_tokens 和 completion_tokens
2. THE LLM_Client SHALL 根据模型定价计算每次调用的成本
3. THE LLM_Client SHALL 提供查询累计 token 使用量和成本的方法
4. THE LLM_Client SHALL 支持按 task_type 分组统计成本
5. THE LLM_Client SHALL 将成本数据写入 Ledger

### 需求 6：流式响应支持

**用户故事：** 作为 Agent 开发者，我希望能够使用流式响应，以便实时显示 LLM 输出。

#### 验收标准

1. THE LLM_Client SHALL 支持 streaming 模式
2. WHEN streaming 启用时，THE LLM_Client SHALL 逐步返回 LLM 输出
3. WHEN streaming 模式下返回 function call 时，THE LLM_Client SHALL 等待完整的 function call 后再返回
4. THE LLM_Client SHALL 支持在 streaming 模式下追踪 token 使用量
5. THE LLM_Client SHALL 提供同步和异步的 streaming API

### 需求 7：上下文窗口管理

**用户故事：** 作为 Agent 运行时，我希望能够管理上下文窗口，以便避免超出模型限制。

#### 验收标准

1. THE LLM_Client SHALL 提供估算 prompt token 数的方法
2. WHEN prompt 超出模型上下文窗口时，THE LLM_Client SHALL 抛出清晰的错误
3. THE LLM_Client SHALL 提供截断 prompt 的方法（保留重要部分）
4. THE LLM_Client SHALL 支持配置每个模型的上下文窗口大小
5. THE LLM_Client SHALL 在日志中记录 prompt token 数和窗口使用率

### 需求 8：Prompt 构建和模板

**用户故事：** 作为 Agent 运行时，我希望能够方便地构建 system prompt，以便注入身份、记忆、知识。

#### 验收标准

1. THE LLM_Client SHALL 提供构建 messages 列表的辅助方法
2. THE LLM_Client SHALL 支持 system、user、assistant 角色的消息
3. THE LLM_Client SHALL 支持在 system prompt 中注入变量（如 Skills 知识）
4. THE LLM_Client SHALL 提供格式化 function call 结果为 assistant 消息的方法
5. THE LLM_Client SHALL 支持多轮对话的消息历史管理

### 需求 9：错误处理和日志

**用户故事：** 作为 OwlClaw 开发者，我希望 LLM 调用失败时能够获得清晰的错误信息，以便快速定位问题。

#### 验收标准

1. WHEN API key 无效时，THE LLM_Client SHALL 抛出 AuthenticationError
2. WHEN rate limit 触发时，THE LLM_Client SHALL 抛出 RateLimitError 并自动重试
3. WHEN 请求格式错误时，THE LLM_Client SHALL 抛出 ValidationError 并包含详细信息
4. WHEN 模型不可用时，THE LLM_Client SHALL 抛出 ServiceUnavailableError 并尝试 fallback
5. THE LLM_Client SHALL 记录所有 LLM 调用的日志（模型、token、延迟、成本）

### 需求 10：与 Langfuse 集成

**用户故事：** 作为 OwlClaw 运维者，我希望 LLM 调用能够自动追踪到 Langfuse，以便可视化和分析。

#### 验收标准

1. THE LLM_Client SHALL 支持配置 Langfuse 集成
2. WHEN Langfuse 启用时，THE LLM_Client SHALL 自动创建 trace
3. WHEN 调用 LLM 时，THE LLM_Client SHALL 记录 prompt、response、tokens、cost 到 Langfuse
4. WHEN function calling 时，THE LLM_Client SHALL 记录 tools 和 function call 结果
5. THE LLM_Client SHALL 支持为每个 Agent run 创建独立的 trace

### 需求 11：模型特定优化

**用户故事：** 作为 OwlClaw 开发者，我希望能够针对不同模型进行优化，以便充分利用各模型的特性。

#### 验收标准

1. THE LLM_Client SHALL 支持 OpenAI 的 parallel function calling
2. THE LLM_Client SHALL 支持 Anthropic 的 thinking 模式
3. THE LLM_Client SHALL 支持 Google 的 grounding 和 search
4. THE LLM_Client SHALL 自动处理不同模型的 function calling 格式差异
5. THE LLM_Client SHALL 提供查询模型能力（是否支持 function calling、vision 等）的方法

### 需求 12：测试和模拟

**用户故事：** 作为 OwlClaw 开发者，我希望能够在测试环境中模拟 LLM 调用，以便不消耗真实 API 配额。

#### 验收标准

1. THE LLM_Client SHALL 支持 mock 模式
2. WHEN mock 模式启用时，THE LLM_Client SHALL 返回预定义的响应
3. THE LLM_Client SHALL 支持配置 mock 响应（文本、function call）
4. THE LLM_Client SHALL 在 mock 模式下仍然追踪 token 使用量（模拟值）
5. THE LLM_Client SHALL 提供验证 prompt 格式的方法（不实际调用 LLM）

