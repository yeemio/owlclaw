# 设计文档

## 文档联动

- requirements: `.kiro/specs/integrations-llm/requirements.md`
- design: `.kiro/specs/integrations-llm/design.md`
- tasks: `.kiro/specs/integrations-llm/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 简介

本文档描述 OwlClaw 与 litellm 的集成设计。litellm 为 OwlClaw 提供统一的 LLM 调用接口，支持 100+ 模型提供商。集成采用隔离设计，所有 litellm 相关代码集中在 `owlclaw/integrations/llm.py` 中。

## 架构概览

```
OwlClaw Agent Runtime
    ↓
owlclaw/integrations/llm.py (隔离层)
    ↓
litellm
    ↓
OpenAI / Anthropic / Google / Azure / ...
```

### 集成边界

**OwlClaw 自建部分：**
- Agent 运行时（身份、记忆、知识注入）
- Function calling 工具列表构建
- 模型路由（task_type → 模型）
- 成本追踪和预算控制

**litellm 提供部分：**
- 统一的 LLM 调用接口
- 100+ 模型支持
- 自动重试和降级
- Token 计数和成本计算

**隔离层职责：**
- 封装 litellm 的复杂性
- 提供 OwlClaw 风格的 API
- 处理配置和模型路由
- 集成 Langfuse tracing



## 组件设计

### 1. LLMConfig

**职责：** LLM 配置管理（使用 Pydantic）。

#### 1.1 配置结构

```python
from pydantic import BaseModel
from typing import Optional, Dict, List

class ModelConfig(BaseModel):
    """单个模型的配置"""
    name: str  # 如 "gpt-4o", "claude-3-5-sonnet"
    provider: str  # 如 "openai", "anthropic"
    api_key_env: str  # 环境变量名，如 "OPENAI_API_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 128000
    supports_function_calling: bool = True
    cost_per_1k_prompt_tokens: float = 0.0
    cost_per_1k_completion_tokens: float = 0.0


class TaskTypeRouting(BaseModel):
    """task_type 到模型的路由配置"""
    task_type: str
    model: str
    fallback_models: List[str] = []
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class LLMConfig(BaseModel):
    """LLM 集成配置"""
    default_model: str = "gpt-4o"
    models: Dict[str, ModelConfig]
    task_type_routing: List[TaskTypeRouting] = []
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Langfuse 集成
    langfuse_enabled: bool = False
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Mock 模式（测试用）
    mock_mode: bool = False
    mock_responses: Dict[str, str] = {}
    
    @classmethod
    def from_yaml(cls, config_path: str) -> "LLMConfig":
        """从 owlclaw.yaml 加载配置"""
        ...
```

#### 1.2 配置示例（owlclaw.yaml）

```yaml
llm:
  default_model: gpt-4o
  
  models:
    gpt-4o:
      name: gpt-4o
      provider: openai
      api_key_env: OPENAI_API_KEY
      temperature: 0.7
      max_tokens: 4096
      context_window: 128000
      supports_function_calling: true
      cost_per_1k_prompt_tokens: 0.005
      cost_per_1k_completion_tokens: 0.015
    
    gpt-4o-mini:
      name: gpt-4o-mini
      provider: openai
      api_key_env: OPENAI_API_KEY
      temperature: 0.7
      max_tokens: 4096
      context_window: 128000
      supports_function_calling: true
      cost_per_1k_prompt_tokens: 0.00015
      cost_per_1k_completion_tokens: 0.0006
    
    claude-3-5-sonnet:
      name: claude-3-5-sonnet-20241022
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY
      temperature: 0.7
      max_tokens: 8192
      context_window: 200000
      supports_function_calling: true
      cost_per_1k_prompt_tokens: 0.003
      cost_per_1k_completion_tokens: 0.015
  
  task_type_routing:
    - task_type: trading_decision
      model: gpt-4o
      fallback_models: [claude-3-5-sonnet, gpt-4o-mini]
      temperature: 0.3
    
    - task_type: knowledge_generation
      model: claude-3-5-sonnet
      fallback_models: [gpt-4o]
      temperature: 0.7
    
    - task_type: simple_query
      model: gpt-4o-mini
      fallback_models: [gpt-4o]
  
  max_retries: 3
  retry_delay_seconds: 1.0
  
  langfuse_enabled: true
  langfuse_public_key: ${LANGFUSE_PUBLIC_KEY}
  langfuse_secret_key: ${LANGFUSE_SECRET_KEY}
```



### 2. LLMClient

**职责：** 封装 litellm，提供 OwlClaw 风格的 API。

#### 2.1 类定义

```python
from typing import List, Dict, Any, Optional, AsyncIterator
import litellm
from langfuse import Langfuse

class LLMResponse:
    """LLM 响应的统一格式"""
    def __init__(
        self,
        content: Optional[str],
        function_calls: List[Dict[str, Any]],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ):
        self.content = content
        self.function_calls = function_calls
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.cost = cost


class LLMClient:
    """OwlClaw 对 litellm 的封装客户端"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._langfuse: Optional[Langfuse] = None
        
        # 初始化 Langfuse
        if config.langfuse_enabled:
            self._langfuse = Langfuse(
                public_key=config.langfuse_public_key,
                secret_key=config.langfuse_secret_key,
                host=config.langfuse_host,
            )
        
        # 配置 litellm
        litellm.set_verbose = False
        litellm.drop_params = True  # 自动移除不支持的参数
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        task_type: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """调用 LLM 完成任务
        
        Args:
            messages: 消息列表（system, user, assistant）
            tools: Function calling 工具列表
            task_type: 任务类型（用于模型路由）
            temperature: 温度参数（覆盖配置）
            max_tokens: 最大 token 数（覆盖配置）
            stream: 是否使用流式响应
        
        Returns:
            LLMResponse 对象
        """
        # 1. 模型路由
        model_name, model_config = self._route_model(task_type)
        
        # 2. 参数准备
        call_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature or model_config.temperature,
            "max_tokens": max_tokens or model_config.max_tokens,
        }
        
        if tools:
            call_params["tools"] = tools
            call_params["tool_choice"] = "auto"
        
        # 3. Langfuse trace
        trace = None
        if self._langfuse:
            trace = self._langfuse.trace(
                name="llm_call",
                metadata={"task_type": task_type, "model": model_name},
            )
        
        # 4. 调用 litellm（带重试和降级）
        try:
            response = await self._call_with_fallback(
                call_params,
                model_config.fallback_models if task_type else [],
            )
        except Exception as e:
            if trace:
                trace.update(status="error", output=str(e))
            raise
        
        # 5. 解析响应
        llm_response = self._parse_response(response, model_name)
        
        # 6. 记录到 Langfuse
        if trace:
            trace.generation(
                name="completion",
                model=model_name,
                input=messages,
                output=llm_response.content or llm_response.function_calls,
                usage={
                    "prompt_tokens": llm_response.prompt_tokens,
                    "completion_tokens": llm_response.completion_tokens,
                    "total_tokens": llm_response.total_tokens,
                },
                metadata={"cost": llm_response.cost},
            )
        
        return llm_response
    
    def _route_model(self, task_type: Optional[str]) -> tuple[str, ModelConfig]:
        """根据 task_type 路由到模型"""
        if task_type:
            for routing in self.config.task_type_routing:
                if routing.task_type == task_type:
                    model_name = routing.model
                    return model_name, self.config.models[model_name]
        
        # 使用默认模型
        model_name = self.config.default_model
        return model_name, self.config.models[model_name]
    
    async def _call_with_fallback(
        self,
        params: Dict[str, Any],
        fallback_models: List[str],
    ) -> Any:
        """调用 LLM，失败时尝试 fallback 模型"""
        models_to_try = [params["model"]] + fallback_models
        
        last_error = None
        for model in models_to_try:
            try:
                params["model"] = model
                response = await litellm.acompletion(**params)
                return response
            except litellm.RateLimitError as e:
                # Rate limit 错误，重试
                last_error = e
                await asyncio.sleep(self.config.retry_delay_seconds)
                continue
            except litellm.AuthenticationError as e:
                # 认证错误，不重试
                raise
            except Exception as e:
                # 其他错误，尝试下一个模型
                last_error = e
                continue
        
        # 所有模型都失败
        raise RuntimeError(
            f"All models failed. Last error: {last_error}"
        )
    
    def _parse_response(self, response: Any, model: str) -> LLMResponse:
        """解析 litellm 响应"""
        choice = response.choices[0]
        message = choice.message
        
        # 提取 function calls
        function_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                function_calls.append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                })
        
        # 计算成本
        model_config = self.config.models[model]
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        cost = (
            prompt_tokens / 1000 * model_config.cost_per_1k_prompt_tokens +
            completion_tokens / 1000 * model_config.cost_per_1k_completion_tokens
        )
        
        return LLMResponse(
            content=message.content,
            function_calls=function_calls,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )
```



### 3. 辅助方法

#### 3.1 Prompt 构建

```python
class PromptBuilder:
    """辅助构建 LLM messages"""
    
    @staticmethod
    def build_system_message(
        soul: str,
        identity: str,
        skills_knowledge: str,
        recent_memory: str,
    ) -> Dict[str, str]:
        """构建 system message"""
        return {
            "role": "system",
            "content": f"{soul}\n\n{identity}\n\n{skills_knowledge}\n\n{recent_memory}",
        }
    
    @staticmethod
    def build_user_message(content: str) -> Dict[str, str]:
        """构建 user message"""
        return {"role": "user", "content": content}
    
    @staticmethod
    def build_function_result_message(
        function_call_id: str,
        function_name: str,
        result: Any,
    ) -> Dict[str, str]:
        """构建 function call 结果消息"""
        return {
            "role": "tool",
            "tool_call_id": function_call_id,
            "name": function_name,
            "content": json.dumps(result),
        }
```

#### 3.2 Tools 格式转换

```python
class ToolsConverter:
    """将 OwlClaw capabilities 转换为 LLM tools 格式"""
    
    @staticmethod
    def capabilities_to_tools(
        capabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """转换 capabilities 为 OpenAI function calling 格式"""
        tools = []
        
        for cap in capabilities:
            tools.append({
                "type": "function",
                "function": {
                    "name": cap["name"],
                    "description": cap["description"],
                    "parameters": cap.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                },
            })
        
        return tools
```

#### 3.3 Token 估算

```python
class TokenEstimator:
    """估算 prompt token 数"""
    
    @staticmethod
    def estimate_tokens(text: str, model: str = "gpt-4") -> int:
        """估算文本的 token 数
        
        使用 tiktoken 库进行准确估算
        """
        import tiktoken
        
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    
    @staticmethod
    def check_context_window(
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
    ) -> bool:
        """检查是否超出上下文窗口"""
        total_tokens = sum(
            TokenEstimator.estimate_tokens(msg["content"], model_config.name)
            for msg in messages
        )
        
        return total_tokens <= model_config.context_window
```



## 错误处理

### 1. 认证错误

```python
# 场景：API key 无效
# 行为：抛出 AuthenticationError

AuthenticationError: Invalid API key for model 'gpt-4o'
  Provider: openai
  Check environment variable: OPENAI_API_KEY
```

### 2. Rate Limit 错误

```python
# 场景：超出 API 速率限制
# 行为：自动重试（带延迟）

[WARNING] Rate limit exceeded for model 'gpt-4o' (attempt 1/3)
[INFO] Retrying in 1.0 seconds...
[WARNING] Rate limit exceeded for model 'gpt-4o' (attempt 2/3)
[INFO] Retrying in 1.0 seconds...
[SUCCESS] Request succeeded on attempt 3
```

### 3. 模型降级

```python
# 场景：主模型不可用
# 行为：自动切换到 fallback 模型

[ERROR] Model 'gpt-4o' unavailable: ServiceUnavailableError
[INFO] Falling back to 'claude-3-5-sonnet'
[SUCCESS] Request succeeded with fallback model
```

### 4. 上下文窗口超限

```python
# 场景：prompt 超出模型上下文窗口
# 行为：抛出 ContextWindowExceededError

ContextWindowExceededError: Prompt exceeds context window
  Model: gpt-4o
  Context window: 128000 tokens
  Prompt tokens: 135000 tokens
  Suggestion: Truncate prompt or use a model with larger context window
```

## 测试策略

### 1. 单元测试

```python
def test_llm_config_from_yaml():
    # Given: 有效的 owlclaw.yaml
    # When: 加载配置
    # Then: 返回 LLMConfig 对象
    
def test_model_routing():
    # Given: task_type 配置
    # When: 调用 _route_model()
    # Then: 返回正确的模型
    
def test_capabilities_to_tools():
    # Given: capabilities 列表
    # When: 转换为 tools 格式
    # Then: 返回 OpenAI function calling 格式
    
def test_token_estimation():
    # Given: 文本字符串
    # When: 估算 token 数
    # Then: 返回合理的估算值
```

### 2. 集成测试

```python
@pytest.mark.integration
async def test_llm_call_with_function_calling():
    # Given: LLMClient 和 tools
    # When: 调用 complete()
    # Then: 返回 function calls
    
@pytest.mark.integration
async def test_model_fallback():
    # Given: 主模型不可用
    # When: 调用 complete()
    # Then: 自动切换到 fallback 模型
    
@pytest.mark.integration
async def test_langfuse_tracing():
    # Given: Langfuse 启用
    # When: 调用 complete()
    # Then: trace 记录到 Langfuse
```

### 3. Mock 模式测试

```python
def test_mock_mode():
    # Given: mock_mode = True
    # When: 调用 complete()
    # Then: 返回预定义的响应，不调用真实 API
```

## 依赖关系

### 外部依赖

- **litellm** (`litellm`): LLM 统一接口
- **tiktoken** (`tiktoken`): Token 计数
- **langfuse** (`langfuse`): 可观测性（可选）
- **pydantic** (`pydantic`): 配置验证

### 内部依赖

- **owlclaw.agent.runtime**: Agent 运行时将使用 LLMClient 调用 LLM
- **owlclaw.capabilities.registry**: 提供 capabilities 列表用于 function calling
- **owlclaw.governance.ledger**: 接收成本数据

## 未来扩展

### 1. 缓存支持

**需求：** 相同 prompt 的响应缓存，减少 API 调用。

**实现：**
- 使用 Redis 或内存缓存
- 缓存 key = hash(messages + tools)
- 配置缓存 TTL

### 2. 批量调用

**需求：** 批量调用多个 LLM 请求，提高吞吐量。

**实现：**
- `batch_complete(requests: List[...]) -> List[LLMResponse]`
- 并发调用，控制并发数

### 3. 自定义模型

**需求：** 支持本地部署的模型（如 Ollama）。

**实现：**
- 配置 `custom_endpoint`
- litellm 支持自定义 API endpoint

## 安全考虑

### 1. API Key 管理

**风险：** API key 泄露导致未授权使用。

**缓解：**
- 从环境变量读取（不写入配置文件）
- 使用 secrets 管理工具（如 AWS Secrets Manager）
- 定期轮换 API keys

### 2. Prompt Injection

**风险：** 恶意输入注入到 prompt 中。

**缓解：**
- 外部输入作为 user 消息，不混入 system prompt
- 验证和清理外部输入
- 使用 LLM 的 safety 功能

### 3. 成本控制

**风险：** 恶意或错误的调用导致成本失控。

**缓解：**
- 配置月度预算上限
- 治理层的预算过滤
- 实时成本监控和告警

