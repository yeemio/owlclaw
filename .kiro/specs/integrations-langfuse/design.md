# 设计文档：Langfuse 集成

## 文档联动

- requirements: `.kiro/specs/integrations-langfuse/requirements.md`
- design: `.kiro/specs/integrations-langfuse/design.md`
- tasks: `.kiro/specs/integrations-langfuse/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

本文档描述了将 Langfuse 可观测性集成到 OwlClaw Agent 系统的设计。Langfuse 为 Agent 运行提供 LLM 调用追踪、成本分析和可观测性能力。

该集成遵循隔离设计模式，所有 Langfuse 相关代码集中在 `owlclaw/integrations/langfuse.py` 中，使得未来替换或支持其他可观测性平台变得容易。

### 核心设计原则

1. **隔离性**：所有 Langfuse 逻辑隔离在单一模块中
2. **非阻塞**：追踪上报是异步的，不阻塞 Agent 执行
3. **优雅降级**：Langfuse 不可用时系统继续正常运行
4. **隐私优先**：内置敏感信息脱敏支持
5. **最小侵入**：自动创建追踪，无需手动埋点

### 设计目标

- 为每次 Agent Run 创建完整的 LLM 调用链追踪
- 精确统计 token 使用量和成本
- 监控 LLM 调用延迟和成功率
- 支持人工标注和自动评分
- 与 Agent Runtime 无缝集成

## 架构

### 系统上下文

```
OwlClaw Agent Runtime
    ↓
owlclaw/integrations/langfuse.py (隔离层)
    ↓
Langfuse Python SDK
    ↓
Langfuse Server (云端或自托管)
    ↓
PostgreSQL (Langfuse 数据存储)
```

### 集成边界

**OwlClaw 组件：**
- Agent Runtime (身份、记忆、知识、决策循环)
- LLM Client (litellm 集成)
- 工具执行系统
- 治理层

**Langfuse 组件：**
- Trace 和 Span 管理
- Token 使用统计
- 成本计算和聚合
- 延迟和成功率监控
- 人工标注和评分
- Dashboard UI

**隔离层职责：**
- 封装 Langfuse SDK 复杂性
- 提供 OwlClaw 风格的 API
- 处理配置和连接管理
- 异步上报和批量处理
- Langfuse 不可用时优雅降级
- 隐私保护（脱敏敏感数据）

### 数据流

```
Agent Run 开始
    ↓
创建 Trace (trace_id, agent_id, run_id)
    ↓
决策循环
    ├─ LLM 调用 → 创建 LLM Span (prompt, response, tokens, cost)
    ├─ 工具调用 → 创建 Tool Span (input, output, duration)
    └─ 重复...
    ↓
Agent Run 结束
    ↓
结束 Trace (total_cost, total_duration)
    ↓
异步上报到 Langfuse Server
```

### 组件架构

```
owlclaw/integrations/langfuse.py
├─ LangfuseClient (主客户端)
│  ├─ __init__(config) - 初始化连接
│  ├─ create_trace() - 创建 trace
│  ├─ create_llm_span() - 创建 LLM span
│  ├─ create_tool_span() - 创建工具 span
│  ├─ end_trace() - 结束 trace
│  └─ flush() - 刷新待上报数据
│
├─ TraceContext (上下文管理)
│  ├─ trace_id - Trace ID
│  ├─ parent_span_id - 父 Span ID
│  └─ metadata - 元数据
│
├─ TokenCalculator (Token 计算)
│  ├─ calculate_tokens() - 计算 token 数量
│  └─ calculate_cost() - 计算成本
│
├─ PrivacyMasker (隐私脱敏)
│  ├─ mask_pii() - 脱敏 PII
│  ├─ mask_secrets() - 脱敏密钥
│  └─ apply_custom_rules() - 应用自定义规则
│
└─ Config (配置管理)
   ├─ enabled - 是否启用
   ├─ credentials - 认证信息
   ├─ sampling_rate - 采样率
   └─ privacy_settings - 隐私设置
```

## 组件和接口

### 1. LangfuseClient

主客户端类，封装所有 Langfuse 交互。


#### 接口定义

```python
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class SpanType(Enum):
    """Span 类型"""
    LLM = "llm"
    TOOL = "tool"
    GENERATION = "generation"
    SPAN = "span"

@dataclass
class LangfuseConfig:
    """Langfuse 配置"""
    enabled: bool = True
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"
    
    # 采样配置
    sampling_rate: float = 1.0  # 1.0 = 100% 采样
    
    # 异步上报配置
    async_upload: bool = True
    batch_size: int = 10
    flush_interval_seconds: int = 5
    
    # 隐私配置
    mask_inputs: bool = False
    mask_outputs: bool = False
    custom_mask_patterns: List[str] = None

@dataclass
class TraceMetadata:
    """Trace 元数据"""
    agent_id: str
    run_id: str
    trigger_type: str
    focus: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class LLMSpanData:
    """LLM Span 数据"""
    model: str
    prompt: List[Dict[str, str]]  # messages
    response: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    status: str  # "success" or "error"
    error_message: Optional[str] = None

@dataclass
class ToolSpanData:
    """Tool Span 数据"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    duration_ms: float
    status: str  # "success" or "error"
    error_message: Optional[str] = None

class LangfuseClient:
    """Langfuse 客户端"""
    
    def __init__(self, config: LangfuseConfig):
        """
        初始化 Langfuse 客户端
        
        Args:
            config: Langfuse 配置
        """
        self.config = config
        self._client: Optional[Any] = None
        self._enabled = config.enabled
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """初始化 Langfuse SDK 客户端"""
        if not self._enabled:
            return
        
        try:
            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=self.config.public_key,
                secret_key=self.config.secret_key,
                host=self.config.host,
            )
        except Exception as e:
            # 降级：初始化失败时禁用
            self._enabled = False
            logger.warning(f"Failed to initialize Langfuse client: {e}")
    
    def create_trace(
        self,
        name: str,
        metadata: TraceMetadata,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        创建 Trace
        
        Args:
            name: Trace 名称
            metadata: Trace 元数据
            tags: 标签列表
        
        Returns:
            trace_id: Trace ID，如果禁用则返回 None
        """
        if not self._enabled or not self._should_sample():
            return None
        
        try:
            trace = self._client.trace(
                name=name,
                metadata={
                    "agent_id": metadata.agent_id,
                    "run_id": metadata.run_id,
                    "trigger_type": metadata.trigger_type,
                    "focus": metadata.focus,
                    "user_id": metadata.user_id,
                    "session_id": metadata.session_id,
                },
                tags=tags or [],
            )
            return trace.id
        except Exception as e:
            logger.warning(f"Failed to create trace: {e}")
            return None
    
    def create_llm_span(
        self,
        trace_id: str,
        span_name: str,
        data: LLMSpanData,
        parent_span_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        创建 LLM Span
        
        Args:
            trace_id: Trace ID
            span_name: Span 名称
            data: LLM Span 数据
            parent_span_id: 父 Span ID
        
        Returns:
            span_id: Span ID，如果禁用则返回 None
        """
        if not self._enabled or not trace_id:
            return None
        
        try:
            # 应用隐私脱敏
            masked_prompt = self._mask_data(data.prompt) if self.config.mask_inputs else data.prompt
            masked_response = self._mask_data(data.response) if self.config.mask_outputs else data.response
            
            generation = self._client.generation(
                trace_id=trace_id,
                name=span_name,
                model=data.model,
                input=masked_prompt,
                output=masked_response,
                usage={
                    "prompt_tokens": data.prompt_tokens,
                    "completion_tokens": data.completion_tokens,
                    "total_tokens": data.total_tokens,
                },
                metadata={
                    "cost_usd": data.cost_usd,
                    "latency_ms": data.latency_ms,
                    "status": data.status,
                    "error_message": data.error_message,
                },
                parent_observation_id=parent_span_id,
            )
            return generation.id
        except Exception as e:
            logger.warning(f"Failed to create LLM span: {e}")
            return None
    
    def create_tool_span(
        self,
        trace_id: str,
        span_name: str,
        data: ToolSpanData,
        parent_span_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        创建 Tool Span
        
        Args:
            trace_id: Trace ID
            span_name: Span 名称
            data: Tool Span 数据
            parent_span_id: 父 Span ID
        
        Returns:
            span_id: Span ID，如果禁用则返回 None
        """
        if not self._enabled or not trace_id:
            return None
        
        try:
            # 应用隐私脱敏
            masked_args = self._mask_data(data.arguments) if self.config.mask_inputs else data.arguments
            masked_result = self._mask_data(data.result) if self.config.mask_outputs else data.result
            
            span = self._client.span(
                trace_id=trace_id,
                name=span_name,
                input={"tool_name": data.tool_name, "arguments": masked_args},
                output=masked_result,
                metadata={
                    "duration_ms": data.duration_ms,
                    "status": data.status,
                    "error_message": data.error_message,
                },
                parent_observation_id=parent_span_id,
            )
            return span.id
        except Exception as e:
            logger.warning(f"Failed to create tool span: {e}")
            return None
    
    def end_trace(
        self,
        trace_id: str,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        结束 Trace
        
        Args:
            trace_id: Trace ID
            output: Trace 输出
            metadata: 额外元数据
        """
        if not self._enabled or not trace_id:
            return
        
        try:
            self._client.trace(
                id=trace_id,
                output=output,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to end trace: {e}")
    
    def flush(self) -> None:
        """刷新所有待上报的数据"""
        if not self._enabled or not self._client:
            return
        
        try:
            self._client.flush()
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse client: {e}")
    
    def _should_sample(self) -> bool:
        """判断是否应该采样"""
        import random
        return random.random() < self.config.sampling_rate
    
    def _mask_data(self, data: Any) -> Any:
        """脱敏数据"""
        # 实现在 PrivacyMasker 中
        return PrivacyMasker.mask(data, self.config)
```

### 2. TraceContext

上下文管理器，用于在 Agent Run 生命周期中传递 trace 信息。

```python
from contextvars import ContextVar
from typing import Optional

# 使用 contextvars 在异步环境中传递上下文
_trace_context: ContextVar[Optional['TraceContext']] = ContextVar('trace_context', default=None)

@dataclass
class TraceContext:
    """Trace 上下文"""
    trace_id: str
    parent_span_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_current(cls) -> Optional['TraceContext']:
        """获取当前上下文"""
        return _trace_context.get()
    
    @classmethod
    def set_current(cls, context: Optional['TraceContext']) -> None:
        """设置当前上下文"""
        _trace_context.set(context)
    
    def with_parent_span(self, span_id: str) -> 'TraceContext':
        """创建带有父 Span 的新上下文"""
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=span_id,
            metadata=self.metadata,
        )
```

### 3. TokenCalculator

Token 计算和成本估算。

```python
from typing import Dict, Tuple

class TokenCalculator:
    """Token 计算器"""
    
    # 模型定价表 (USD per 1K tokens)
    MODEL_PRICING = {
        "gpt-4": {
            "prompt": 0.03 / 1000,
            "completion": 0.06 / 1000,
        },
        "gpt-4-turbo": {
            "prompt": 0.01 / 1000,
            "completion": 0.03 / 1000,
        },
        "gpt-3.5-turbo": {
            "prompt": 0.0015 / 1000,
            "completion": 0.002 / 1000,
        },
        "claude-3-opus": {
            "prompt": 0.015 / 1000,
            "completion": 0.075 / 1000,
        },
        "claude-3-sonnet": {
            "prompt": 0.003 / 1000,
            "completion": 0.015 / 1000,
        },
        "claude-3-haiku": {
            "prompt": 0.00025 / 1000,
            "completion": 0.00125 / 1000,
        },
    }
    
    @classmethod
    def calculate_cost(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        计算成本
        
        Args:
            model: 模型名称
            prompt_tokens: Prompt token 数量
            completion_tokens: Completion token 数量
        
        Returns:
            cost_usd: 成本（USD）
        """
        # 标准化模型名称
        normalized_model = cls._normalize_model_name(model)
        
        # 获取定价
        pricing = cls.MODEL_PRICING.get(normalized_model)
        if not pricing:
            logger.warning(f"Unknown model pricing: {model}, using default")
            pricing = cls.MODEL_PRICING["gpt-3.5-turbo"]
        
        # 计算成本
        prompt_cost = prompt_tokens * pricing["prompt"]
        completion_cost = completion_tokens * pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        return round(total_cost, 6)  # 保留 6 位小数
    
    @classmethod
    def _normalize_model_name(cls, model: str) -> str:
        """标准化模型名称"""
        # 移除版本号和日期
        # 例如: "gpt-4-0613" -> "gpt-4"
        model = model.lower()
        
        if model.startswith("gpt-4-turbo"):
            return "gpt-4-turbo"
        elif model.startswith("gpt-4"):
            return "gpt-4"
        elif model.startswith("gpt-3.5"):
            return "gpt-3.5-turbo"
        elif "claude-3-opus" in model:
            return "claude-3-opus"
        elif "claude-3-sonnet" in model:
            return "claude-3-sonnet"
        elif "claude-3-haiku" in model:
            return "claude-3-haiku"
        
        return model
    
    @classmethod
    def extract_tokens_from_response(cls, response: Any) -> Tuple[int, int, int]:
        """
        从 LLM 响应中提取 token 数量
        
        Args:
            response: LLM 响应对象
        
        Returns:
            (prompt_tokens, completion_tokens, total_tokens)
        """
        try:
            # litellm 响应格式
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            return prompt_tokens, completion_tokens, total_tokens
        except Exception as e:
            logger.warning(f"Failed to extract tokens from response: {e}")
            return 0, 0, 0
```

### 4. PrivacyMasker

隐私脱敏工具。

```python
import re
from typing import Any, List, Pattern

class PrivacyMasker:
    """隐私脱敏器"""
    
    # 预定义的脱敏模式
    PII_PATTERNS = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "credit_card": re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    }
    
    SECRET_PATTERNS = {
        "api_key": re.compile(r'\b[A-Za-z0-9_-]{32,}\b'),
        "bearer_token": re.compile(r'Bearer\s+[A-Za-z0-9_-]+'),
        "password": re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'}\s]+)'),
    }
    
    @classmethod
    def mask(cls, data: Any, config: LangfuseConfig) -> Any:
        """
        脱敏数据
        
        Args:
            data: 原始数据
            config: 配置
        
        Returns:
            脱敏后的数据
        """
        if isinstance(data, str):
            return cls._mask_string(data, config)
        elif isinstance(data, dict):
            return {k: cls.mask(v, config) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.mask(item, config) for item in data]
        else:
            return data
    
    @classmethod
    def _mask_string(cls, text: str, config: LangfuseConfig) -> str:
        """脱敏字符串"""
        # 脱敏 PII
        for name, pattern in cls.PII_PATTERNS.items():
            text = pattern.sub(f"[MASKED_{name.upper()}]", text)
        
        # 脱敏密钥
        for name, pattern in cls.SECRET_PATTERNS.items():
            text = pattern.sub(f"[MASKED_{name.upper()}]", text)
        
        # 应用自定义规则
        if config.custom_mask_patterns:
            for pattern_str in config.custom_mask_patterns:
                try:
                    pattern = re.compile(pattern_str)
                    text = pattern.sub("[MASKED_CUSTOM]", text)
                except Exception as e:
                    logger.warning(f"Invalid custom mask pattern: {pattern_str}, {e}")
        
        return text
```

### 5. 与 Agent Runtime 集成

在 Agent Runtime 中自动创建和管理 trace。

```python
# owlclaw/agent/runtime/runtime.py

from owlclaw.integrations.langfuse import (
    LangfuseClient,
    TraceContext,
    TraceMetadata,
    LLMSpanData,
    ToolSpanData,
)

class AgentRuntime:
    """Agent 运行时"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        
        # 初始化 Langfuse 客户端
        self.langfuse = LangfuseClient(config.langfuse)
    
    async def run(self, context: AgentRunContext) -> AgentRunResult:
        """
        执行 Agent Run
        
        Args:
            context: Agent Run 上下文
        
        Returns:
            Agent Run 结果
        """
        # 创建 Trace
        trace_id = self.langfuse.create_trace(
            name=f"agent_run_{context.run_id}",
            metadata=TraceMetadata(
                agent_id=context.agent_id,
                run_id=context.run_id,
                trigger_type=context.trigger.type,
                focus=context.focus,
                user_id=context.user_id,
                session_id=context.session_id,
            ),
            tags=["agent_run", context.agent_id],
        )
        
        # 设置 Trace 上下文
        if trace_id:
            TraceContext.set_current(TraceContext(trace_id=trace_id))
        
        try:
            # 执行决策循环
            result = await self._decision_loop(context)
            
            # 结束 Trace
            if trace_id:
                self.langfuse.end_trace(
                    trace_id=trace_id,
                    output={"result": result.to_dict()},
                    metadata={
                        "total_cost_usd": result.total_cost,
                        "total_duration_ms": result.total_duration,
                        "llm_calls": result.llm_call_count,
                        "tool_calls": result.tool_call_count,
                    },
                )
            
            return result
        except Exception as e:
            # 记录错误
            if trace_id:
                self.langfuse.end_trace(
                    trace_id=trace_id,
                    output={"error": str(e)},
                    metadata={"status": "error"},
                )
            raise
        finally:
            # 清理上下文
            TraceContext.set_current(None)
            
            # 刷新待上报数据
            self.langfuse.flush()
```

### 6. LLM 调用追踪

在 LLM 客户端中自动创建 LLM span。

```python
# owlclaw/integrations/llm.py

import time
from owlclaw.integrations.langfuse import (
    TraceContext,
    LLMSpanData,
    TokenCalculator,
)

class LLMClient:
    """LLM 客户端"""
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        调用 LLM
        
        Args:
            messages: 消息列表
            model: 模型名称
            **kwargs: 其他参数
        
        Returns:
            LLM 响应
        """
        # 获取 Trace 上下文
        trace_ctx = TraceContext.get_current()
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用 LLM
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                **kwargs,
            )
            
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000
            
            # 提取 token 使用量
            prompt_tokens, completion_tokens, total_tokens = \
                TokenCalculator.extract_tokens_from_response(response)
            
            # 计算成本
            cost_usd = TokenCalculator.calculate_cost(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            
            # 创建 LLM Span
            if trace_ctx:
                span_data = LLMSpanData(
                    model=model,
                    prompt=messages,
                    response=response.choices[0].message.content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    status="success",
                )
                
                self.langfuse.create_llm_span(
                    trace_id=trace_ctx.trace_id,
                    span_name=f"llm_call_{model}",
                    data=span_data,
                    parent_span_id=trace_ctx.parent_span_id,
                )
            
            return response
        
        except Exception as e:
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000
            
            # 创建失败的 LLM Span
            if trace_ctx:
                span_data = LLMSpanData(
                    model=model,
                    prompt=messages,
                    response="",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(e),
                )
                
                self.langfuse.create_llm_span(
                    trace_id=trace_ctx.trace_id,
                    span_name=f"llm_call_{model}_error",
                    data=span_data,
                    parent_span_id=trace_ctx.parent_span_id,
                )
            
            raise
```

### 7. 工具调用追踪

在工具执行系统中自动创建 tool span。

```python
# owlclaw/agent/tools.py

import time
from owlclaw.integrations.langfuse import (
    TraceContext,
    ToolSpanData,
)

class ToolExecutor:
    """工具执行器"""
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        # 获取 Trace 上下文
        trace_ctx = TraceContext.get_current()
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 执行工具
            result = await self._execute_tool(tool_name, arguments)
            
            # 计算执行时长
            duration_ms = (time.time() - start_time) * 1000
            
            # 创建 Tool Span
            if trace_ctx:
                span_data = ToolSpanData(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    duration_ms=duration_ms,
                    status="success",
                )
                
                self.langfuse.create_tool_span(
                    trace_id=trace_ctx.trace_id,
                    span_name=f"tool_{tool_name}",
                    data=span_data,
                    parent_span_id=trace_ctx.parent_span_id,
                )
            
            return result
        
        except Exception as e:
            # 计算执行时长
            duration_ms = (time.time() - start_time) * 1000
            
            # 创建失败的 Tool Span
            if trace_ctx:
                span_data = ToolSpanData(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=None,
                    duration_ms=duration_ms,
                    status="error",
                    error_message=str(e),
                )
                
                self.langfuse.create_tool_span(
                    trace_id=trace_ctx.trace_id,
                    span_name=f"tool_{tool_name}_error",
                    data=span_data,
                    parent_span_id=trace_ctx.parent_span_id,
                )
            
            raise
```

## 数据模型

### Trace 数据结构

```python
{
    "id": "trace_abc123",
    "name": "agent_run_run_xyz789",
    "timestamp": "2024-01-15T10:30:00Z",
    "metadata": {
        "agent_id": "agent_001",
        "run_id": "run_xyz789",
        "trigger_type": "scheduled",
        "focus": "daily_report",
        "user_id": "user_123",
        "session_id": "session_456"
    },
    "tags": ["agent_run", "agent_001"],
    "output": {
        "result": {
            "status": "success",
            "message": "Report generated successfully"
        }
    },
    "metadata_final": {
        "total_cost_usd": 0.0245,
        "total_duration_ms": 3500,
        "llm_calls": 3,
        "tool_calls": 2
    }
}
```

### LLM Span 数据结构

```python
{
    "id": "span_llm_001",
    "trace_id": "trace_abc123",
    "parent_observation_id": null,
    "type": "generation",
    "name": "llm_call_gpt-4",
    "timestamp": "2024-01-15T10:30:01Z",
    "input": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Generate a daily report."
        }
    ],
    "output": "Here is your daily report...",
    "model": "gpt-4",
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 300,
        "total_tokens": 450
    },
    "metadata": {
        "cost_usd": 0.0135,
        "latency_ms": 1200,
        "status": "success",
        "error_message": null
    }
}
```

### Tool Span 数据结构

```python
{
    "id": "span_tool_001",
    "trace_id": "trace_abc123",
    "parent_observation_id": "span_llm_001",
    "type": "span",
    "name": "tool_fetch_data",
    "timestamp": "2024-01-15T10:30:02Z",
    "input": {
        "tool_name": "fetch_data",
        "arguments": {
            "source": "database",
            "query": "SELECT * FROM reports WHERE date = '2024-01-15'"
        }
    },
    "output": {
        "rows": 10,
        "data": [...]
    },
    "metadata": {
        "duration_ms": 500,
        "status": "success",
        "error_message": null
    }
}
```



## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：Trace 创建和内容完整性

*对于任意* Agent Run，当系统创建 trace 时，该 trace 应该包含完整的元数据（agent_id、run_id、trigger_type、focus）和时间戳信息。

**验证需求：FR-1.1, FR-1.2, FR-1.3, FR-1.4**

### 属性 2：Trace 嵌套结构

*对于任意* trace 和嵌套的 span 集合，父子关系应该被正确记录，子 span 的 parent_observation_id 应该指向其父 span 的 id。

**验证需求：FR-1.5**

### 属性 3：LLM Span 创建和内容完整性

*对于任意* LLM 调用，当系统创建 LLM span 时，该 span 应该包含完整的输入（prompt）、输出（response）、token 使用量（prompt_tokens、completion_tokens、total_tokens）、成本（cost_usd）、延迟（latency_ms）和状态（status）。

**验证需求：FR-2.1, FR-2.2, FR-2.3, FR-2.4**

### 属性 4：LLM 错误处理

*对于任意* 失败的 LLM 调用，系统应该创建一个状态为 "error" 的 span，并且该 span 应该包含错误信息（error_message）。

**验证需求：FR-2.5**

### 属性 5：Tool Span 创建和内容完整性

*对于任意* 工具调用，当系统创建 tool span 时，该 span 应该包含完整的输入（tool_name、arguments）、输出（result）、执行时长（duration_ms）和状态（status）。

**验证需求：FR-3.1, FR-3.2, FR-3.3, FR-3.4**

### 属性 6：Tool 错误处理

*对于任意* 失败的工具调用，系统应该创建一个状态为 "error" 的 span，并且该 span 应该包含错误信息（error_message）。

**验证需求：FR-3.5**

### 属性 7：Trace 生命周期管理

*对于任意* Agent Run，当 Agent Run 结束时，对应的 trace 应该被正确结束，并且包含最终的输出和元数据（total_cost_usd、total_duration_ms、llm_calls、tool_calls）。

**验证需求：FR-4.2**

### 属性 8：Context 在决策循环中传递

*对于任意* Agent Run，在整个决策循环中，trace context 应该始终可访问，并且 trace_id 保持不变。

**验证需求：FR-5.1**

### 属性 9：Context 在 LLM 调用中可访问

*对于任意* LLM 调用，LLM 客户端应该能够访问当前的 trace context，并使用它创建 LLM span。

**验证需求：FR-5.2**

### 属性 10：Context 在工具执行中可访问

*对于任意* 工具调用，工具执行器应该能够访问当前的 trace context，并使用它创建 tool span。

**验证需求：FR-5.3**

### 属性 11：Token 提取正确性

*对于任意* LLM 响应，系统应该能够正确提取 token 使用量（prompt_tokens、completion_tokens、total_tokens），并且 total_tokens 应该等于 prompt_tokens + completion_tokens。

**验证需求：FR-6.1, FR-6.3**

### 属性 12：成本计算正确性

*对于任意* 模型和 token 使用量，成本计算应该遵循公式：cost = (prompt_tokens × prompt_price) + (completion_tokens × completion_price)，其中价格从定价表中获取。

**验证需求：FR-7.2**

### 属性 13：成本聚合正确性

*对于任意* trace，trace 的总成本应该等于该 trace 下所有 LLM span 的成本之和。

**验证需求：FR-8.1**

### 属性 14：配置验证

*对于任意* 无效的配置（例如缺少 public_key 或 secret_key），系统应该在启动时检测到并拒绝该配置或降级运行。

**验证需求：FR-13.2**

### 属性 15：采样率遵守

*对于任意* 配置的采样率 r（0 ≤ r ≤ 1），在大量 Agent Run 中，实际创建 trace 的比例应该接近 r（允许统计误差）。

**验证需求：FR-13.4**

### 属性 16：PII 脱敏

*对于任意* 包含 PII（邮箱、电话、身份证号、信用卡号）的数据，当启用脱敏时，脱敏后的数据应该不包含原始 PII，而是包含脱敏标记（如 [MASKED_EMAIL]）。

**验证需求：FR-14.2**

### 属性 17：密钥脱敏

*对于任意* 包含密钥（API key、Bearer token、密码）的数据，当启用脱敏时，脱敏后的数据应该不包含原始密钥，而是包含脱敏标记（如 [MASKED_API_KEY]）。

**验证需求：FR-14.3**

### 属性 18：自定义脱敏规则

*对于任意* 自定义脱敏规则（正则表达式），当应用该规则时，匹配该规则的所有内容应该被替换为脱敏标记（[MASKED_CUSTOM]）。

**验证需求：FR-14.4**

### 属性 19：脱敏结构保留

*对于任意* 数据结构（字典、列表、嵌套结构），脱敏操作应该保留原始数据结构，只替换敏感值，不改变键名、列表长度或嵌套层级。

**验证需求：FR-14.5**

### 属性 20：容错降级

*对于任意* Langfuse 不可用的情况（网络错误、服务器错误、认证失败），系统应该降级运行（不创建 trace），记录警告日志，并且不抛出异常导致 Agent Run 失败。

**验证需求：NFR-3.1, NFR-3.2, NFR-3.3**

### 属性 21：数据完整性保证

*对于任意* Agent Run，当 Agent Run 正常结束时，系统应该确保所有创建的 span 都已上报到 Langfuse（通过 flush 操作）。

**验证需求：NFR-4.1**

### 属性 22：日志安全

*对于任意* 日志输出，日志内容应该不包含 API key（public_key 和 secret_key），即使在调试模式下也应该脱敏或省略。

**验证需求：NFR-5.3**

## 错误处理

### 1. Langfuse 不可用

**场景**：Langfuse Server 不可用、网络故障、认证失败

**处理策略**：
- 降级运行：禁用 trace 创建，不影响 Agent Run
- 记录警告日志：记录错误原因和时间
- 不抛出异常：捕获所有 Langfuse 相关异常
- 可选重试：根据配置进行有限次数的重试

**实现**：
```python
def create_trace(self, name: str, metadata: TraceMetadata) -> Optional[str]:
    if not self._enabled:
        return None
    
    try:
        trace = self._client.trace(name=name, metadata=metadata)
        return trace.id
    except Exception as e:
        logger.warning(f"Failed to create trace: {e}")
        # 降级：返回 None，不影响 Agent Run
        return None
```

### 2. LLM 调用失败

**场景**：LLM 超时、返回错误、抛出异常

**处理策略**：
- 创建失败的 LLM span：记录错误信息
- 保留部分数据：记录 prompt、延迟、错误信息
- 向上传播异常：不吞掉 LLM 异常

**实现**：
```python
try:
    response = await litellm.acompletion(...)
    # 创建成功的 span
except Exception as e:
    # 创建失败的 span
    span_data = LLMSpanData(
        model=model,
        prompt=messages,
        response="",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
        latency_ms=latency_ms,
        status="error",
        error_message=str(e),
    )
    self.langfuse.create_llm_span(...)
    raise  # 向上传播异常
```

### 3. 工具执行失败

**场景**：工具超时、返回错误、抛出异常

**处理策略**：
- 创建失败的 tool span：记录错误信息
- 保留部分数据：记录工具名称、参数、执行时长、错误信息
- 向上传播异常：不吞掉工具异常

**实现**：
```python
try:
    result = await self._execute_tool(tool_name, arguments)
    # 创建成功的 span
except Exception as e:
    # 创建失败的 span
    span_data = ToolSpanData(
        tool_name=tool_name,
        arguments=arguments,
        result=None,
        duration_ms=duration_ms,
        status="error",
        error_message=str(e),
    )
    self.langfuse.create_tool_span(...)
    raise  # 向上传播异常
```

### 4. 配置错误

**场景**：缺少必需配置、配置格式错误、认证失败

**处理策略**：
- 启动时验证：在系统启动时检查配置
- 降级运行：配置无效时禁用 Langfuse
- 记录错误日志：明确说明配置问题

**实现**：
```python
def _initialize_client(self) -> None:
    if not self._enabled:
        return
    
    # 验证配置
    if not self.config.public_key or not self.config.secret_key:
        logger.error("Langfuse credentials missing, disabling integration")
        self._enabled = False
        return
    
    try:
        from langfuse import Langfuse
        self._client = Langfuse(...)
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        self._enabled = False
```

### 5. 数据脱敏错误

**场景**：自定义脱敏规则无效、脱敏过程抛出异常

**处理策略**：
- 跳过无效规则：记录警告，继续处理其他规则
- 保护原始数据：脱敏失败时返回原始数据（如果禁用脱敏）或空值（如果启用脱敏）
- 不影响主流程：脱敏错误不应导致 trace 创建失败

**实现**：
```python
def _mask_string(cls, text: str, config: LangfuseConfig) -> str:
    # 应用预定义规则
    for name, pattern in cls.PII_PATTERNS.items():
        try:
            text = pattern.sub(f"[MASKED_{name.upper()}]", text)
        except Exception as e:
            logger.warning(f"Failed to apply {name} mask: {e}")
    
    # 应用自定义规则
    if config.custom_mask_patterns:
        for pattern_str in config.custom_mask_patterns:
            try:
                pattern = re.compile(pattern_str)
                text = pattern.sub("[MASKED_CUSTOM]", text)
            except Exception as e:
                logger.warning(f"Invalid custom mask pattern: {pattern_str}, {e}")
                # 跳过无效规则，继续处理
    
    return text
```

### 6. 进程退出

**场景**：进程正常退出、异常退出、信号终止

**处理策略**：
- 注册退出钩子：使用 atexit 注册 flush 函数
- 刷新待上报数据：确保所有 trace 都已上报
- 设置超时：避免退出时阻塞过久

**实现**：
```python
import atexit

class LangfuseClient:
    def __init__(self, config: LangfuseConfig):
        # ...
        # 注册退出钩子
        atexit.register(self._on_exit)
    
    def _on_exit(self):
        """进程退出时的清理"""
        try:
            logger.info("Flushing Langfuse data before exit")
            self.flush()
        except Exception as e:
            logger.warning(f"Failed to flush on exit: {e}")
```

## 测试策略

### 测试方法

我们采用双重测试方法：

1. **单元测试**：验证特定示例、边界情况和错误条件
2. **属性测试**：验证跨所有输入的通用属性

两者是互补的，对于全面覆盖都是必要的。单元测试捕获具体的 bug，属性测试验证一般正确性。

### 单元测试

单元测试专注于：
- 特定示例：演示正确行为的具体案例
- 集成点：组件之间的交互
- 边界情况和错误条件：特殊情况和异常处理

**示例单元测试**：

```python
# 测试 Trace 创建
def test_create_trace_with_metadata():
    client = LangfuseClient(config)
    metadata = TraceMetadata(
        agent_id="agent_001",
        run_id="run_123",
        trigger_type="scheduled",
        focus="daily_report",
    )
    
    trace_id = client.create_trace("test_trace", metadata)
    
    assert trace_id is not None
    # 验证 trace 包含正确的元数据
    trace = client._client.get_trace(trace_id)
    assert trace.metadata["agent_id"] == "agent_001"
    assert trace.metadata["run_id"] == "run_123"

# 测试 Langfuse 不可用时的降级
def test_graceful_degradation_when_langfuse_unavailable():
    # 使用无效的配置
    config = LangfuseConfig(
        enabled=True,
        public_key="invalid",
        secret_key="invalid",
    )
    
    client = LangfuseClient(config)
    
    # 应该降级，不抛出异常
    trace_id = client.create_trace("test_trace", metadata)
    assert trace_id is None
    assert not client._enabled

# 测试 PII 脱敏
def test_mask_email():
    text = "Contact me at user@example.com"
    masked = PrivacyMasker._mask_string(text, config)
    
    assert "user@example.com" not in masked
    assert "[MASKED_EMAIL]" in masked

# 测试成本计算
def test_calculate_cost_gpt4():
    cost = TokenCalculator.calculate_cost(
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    
    # gpt-4: $0.03/1K prompt, $0.06/1K completion
    expected = (1000 * 0.03 / 1000) + (500 * 0.06 / 1000)
    assert abs(cost - expected) < 0.000001
```

### 属性测试

属性测试专注于：
- 通用属性：应该对所有输入成立的规则
- 通过随机化实现全面的输入覆盖

**配置**：
- 每个属性测试最少 100 次迭代
- 每个测试引用其设计文档属性
- 标签格式：**Feature: integrations-langfuse, Property {number}: {property_text}**

**示例属性测试**：

```python
from hypothesis import given, strategies as st

# Feature: integrations-langfuse, Property 1: Trace 创建和内容完整性
@given(
    agent_id=st.text(min_size=1),
    run_id=st.text(min_size=1),
    trigger_type=st.sampled_from(["scheduled", "manual", "webhook"]),
    focus=st.text(),
)
def test_property_trace_creation_completeness(agent_id, run_id, trigger_type, focus):
    """
    属性 1：对于任意 Agent Run，创建的 trace 应该包含完整的元数据
    """
    client = LangfuseClient(config)
    metadata = TraceMetadata(
        agent_id=agent_id,
        run_id=run_id,
        trigger_type=trigger_type,
        focus=focus,
    )
    
    trace_id = client.create_trace(f"agent_run_{run_id}", metadata)
    
    if trace_id:  # 如果启用了 Langfuse
        trace = client._client.get_trace(trace_id)
        assert trace.metadata["agent_id"] == agent_id
        assert trace.metadata["run_id"] == run_id
        assert trace.metadata["trigger_type"] == trigger_type
        assert trace.metadata["focus"] == focus
        assert trace.timestamp is not None

# Feature: integrations-langfuse, Property 11: Token 提取正确性
@given(
    prompt_tokens=st.integers(min_value=0, max_value=100000),
    completion_tokens=st.integers(min_value=0, max_value=100000),
)
def test_property_token_extraction_correctness(prompt_tokens, completion_tokens):
    """
    属性 11：对于任意 LLM 响应，total_tokens 应该等于 prompt_tokens + completion_tokens
    """
    # 模拟 LLM 响应
    response = {
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
    }
    
    extracted_prompt, extracted_completion, extracted_total = \
        TokenCalculator.extract_tokens_from_response(response)
    
    assert extracted_prompt == prompt_tokens
    assert extracted_completion == completion_tokens
    assert extracted_total == prompt_tokens + completion_tokens

# Feature: integrations-langfuse, Property 12: 成本计算正确性
@given(
    model=st.sampled_from(["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]),
    prompt_tokens=st.integers(min_value=1, max_value=100000),
    completion_tokens=st.integers(min_value=1, max_value=100000),
)
def test_property_cost_calculation_correctness(model, prompt_tokens, completion_tokens):
    """
    属性 12：对于任意模型和 token 使用量，成本计算应该遵循定价公式
    """
    cost = TokenCalculator.calculate_cost(model, prompt_tokens, completion_tokens)
    
    # 获取定价
    normalized_model = TokenCalculator._normalize_model_name(model)
    pricing = TokenCalculator.MODEL_PRICING[normalized_model]
    
    # 手动计算期望成本
    expected_cost = (prompt_tokens * pricing["prompt"]) + \
                    (completion_tokens * pricing["completion"])
    
    # 允许浮点误差
    assert abs(cost - expected_cost) < 0.000001

# Feature: integrations-langfuse, Property 13: 成本聚合正确性
@given(
    span_costs=st.lists(st.floats(min_value=0, max_value=1), min_size=1, max_size=20),
)
def test_property_cost_aggregation_correctness(span_costs):
    """
    属性 13：对于任意 trace，总成本应该等于所有 span 成本之和
    """
    # 创建 trace 和多个 span
    client = LangfuseClient(config)
    trace_id = client.create_trace("test_trace", metadata)
    
    # 创建多个 LLM span
    for i, cost in enumerate(span_costs):
        span_data = LLMSpanData(
            model="gpt-4",
            prompt=[],
            response="",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=cost,
            latency_ms=100,
            status="success",
        )
        client.create_llm_span(trace_id, f"span_{i}", span_data)
    
    # 结束 trace
    expected_total = sum(span_costs)
    client.end_trace(trace_id, metadata={"total_cost_usd": expected_total})
    
    # 验证总成本
    trace = client._client.get_trace(trace_id)
    assert abs(trace.metadata["total_cost_usd"] - expected_total) < 0.000001

# Feature: integrations-langfuse, Property 16: PII 脱敏
@given(
    email=st.emails(),
    text_before=st.text(),
    text_after=st.text(),
)
def test_property_pii_masking_email(email, text_before, text_after):
    """
    属性 16：对于任意包含邮箱的数据，脱敏后应该不包含原始邮箱
    """
    text = f"{text_before} {email} {text_after}"
    config = LangfuseConfig(mask_inputs=True)
    
    masked = PrivacyMasker._mask_string(text, config)
    
    # 原始邮箱不应该出现在脱敏后的文本中
    assert email not in masked
    # 应该包含脱敏标记
    assert "[MASKED_EMAIL]" in masked

# Feature: integrations-langfuse, Property 19: 脱敏结构保留
@given(
    data=st.recursive(
        st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(min_size=1), children, max_size=5),
        ),
        max_leaves=10,
    ),
)
def test_property_masking_preserves_structure(data):
    """
    属性 19：对于任意数据结构，脱敏应该保留原始结构
    """
    config = LangfuseConfig(mask_inputs=True)
    
    masked = PrivacyMasker.mask(data, config)
    
    # 验证结构类型相同
    assert type(masked) == type(data)
    
    # 如果是字典，验证键相同
    if isinstance(data, dict):
        assert set(masked.keys()) == set(data.keys())
    
    # 如果是列表，验证长度相同
    if isinstance(data, list):
        assert len(masked) == len(data)

# Feature: integrations-langfuse, Property 20: 容错降级
@given(
    error_type=st.sampled_from([
        ConnectionError,
        TimeoutError,
        ValueError,
        Exception,
    ]),
)
def test_property_graceful_degradation(error_type):
    """
    属性 20：对于任意 Langfuse 错误，系统应该降级运行不抛出异常
    """
    # 模拟 Langfuse 客户端抛出异常
    client = LangfuseClient(config)
    
    # Mock _client.trace 抛出异常
    original_trace = client._client.trace
    def mock_trace(*args, **kwargs):
        raise error_type("Simulated error")
    client._client.trace = mock_trace
    
    # 应该不抛出异常
    try:
        trace_id = client.create_trace("test_trace", metadata)
        # 应该返回 None（降级）
        assert trace_id is None
    except Exception as e:
        pytest.fail(f"Should not raise exception, but got: {e}")
    finally:
        client._client.trace = original_trace
```

### 测试覆盖率目标

- 单元测试覆盖率：≥ 80%
- 属性测试：覆盖所有 22 个正确性属性
- 集成测试：覆盖端到端流程（Agent Run → Trace → Spans → Langfuse）
- 错误场景测试：覆盖所有 6 种错误处理场景

### 测试工具

- **单元测试框架**：pytest
- **属性测试框架**：hypothesis
- **Mock 工具**：pytest-mock, unittest.mock
- **覆盖率工具**：pytest-cov
- **异步测试**：pytest-asyncio



## 配置管理

### 配置文件格式

使用 YAML 格式配置 Langfuse 集成：

```yaml
# config/agent.yaml

langfuse:
  # 基础配置
  enabled: true
  public_key: "${LANGFUSE_PUBLIC_KEY}"  # 从环境变量读取
  secret_key: "${LANGFUSE_SECRET_KEY}"  # 从环境变量读取
  host: "https://cloud.langfuse.com"    # 或自托管地址
  
  # 采样配置
  sampling_rate: 1.0  # 1.0 = 100% 采样，0.1 = 10% 采样
  
  # 异步上报配置
  async_upload: true
  batch_size: 10              # 批量上报大小
  flush_interval_seconds: 5   # 刷新间隔（秒）
  
  # 隐私配置
  mask_inputs: false   # 是否脱敏输入
  mask_outputs: false  # 是否脱敏输出
  
  # 自定义脱敏规则（正则表达式）
  custom_mask_patterns:
    - "\\b[A-Z0-9]{32}\\b"  # 32 位大写字母数字（可能是 token）
    - "password:\\s*\\S+"   # password: 后面的内容
```

### 环境变量

推荐使用环境变量存储敏感信息：

```bash
# .env

# Langfuse 认证
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# 可选：自托管地址
LANGFUSE_HOST=https://langfuse.example.com
```

### 配置加载

```python
import os
import yaml
from typing import Dict, Any

def load_langfuse_config(config_path: str) -> LangfuseConfig:
    """
    加载 Langfuse 配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        LangfuseConfig 对象
    """
    # 读取配置文件
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    langfuse_config = config_dict.get('langfuse', {})
    
    # 替换环境变量
    langfuse_config = _replace_env_vars(langfuse_config)
    
    # 创建配置对象
    return LangfuseConfig(
        enabled=langfuse_config.get('enabled', True),
        public_key=langfuse_config.get('public_key', ''),
        secret_key=langfuse_config.get('secret_key', ''),
        host=langfuse_config.get('host', 'https://cloud.langfuse.com'),
        sampling_rate=langfuse_config.get('sampling_rate', 1.0),
        async_upload=langfuse_config.get('async_upload', True),
        batch_size=langfuse_config.get('batch_size', 10),
        flush_interval_seconds=langfuse_config.get('flush_interval_seconds', 5),
        mask_inputs=langfuse_config.get('mask_inputs', False),
        mask_outputs=langfuse_config.get('mask_outputs', False),
        custom_mask_patterns=langfuse_config.get('custom_mask_patterns', []),
    )

def _replace_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """替换配置中的环境变量"""
    import re
    
    def replace_value(value):
        if isinstance(value, str):
            # 匹配 ${VAR_NAME} 格式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                env_value = os.getenv(var_name, '')
                value = value.replace(f'${{{var_name}}}', env_value)
            return value
        elif isinstance(value, dict):
            return {k: replace_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [replace_value(item) for item in value]
        else:
            return value
    
    return replace_value(config)
```

### 配置验证

```python
def validate_config(config: LangfuseConfig) -> List[str]:
    """
    验证配置的合法性
    
    Args:
        config: Langfuse 配置
    
    Returns:
        错误列表，如果为空则配置有效
    """
    errors = []
    
    if config.enabled:
        # 检查必需字段
        if not config.public_key:
            errors.append("public_key is required when Langfuse is enabled")
        if not config.secret_key:
            errors.append("secret_key is required when Langfuse is enabled")
        
        # 检查采样率
        if not (0 <= config.sampling_rate <= 1):
            errors.append(f"sampling_rate must be between 0 and 1, got {config.sampling_rate}")
        
        # 检查批量大小
        if config.batch_size <= 0:
            errors.append(f"batch_size must be positive, got {config.batch_size}")
        
        # 检查刷新间隔
        if config.flush_interval_seconds <= 0:
            errors.append(f"flush_interval_seconds must be positive, got {config.flush_interval_seconds}")
        
        # 检查自定义脱敏规则
        for pattern in config.custom_mask_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"Invalid regex pattern '{pattern}': {e}")
    
    return errors
```

### 配置示例

#### 开发环境

```yaml
langfuse:
  enabled: true
  public_key: "${LANGFUSE_PUBLIC_KEY}"
  secret_key: "${LANGFUSE_SECRET_KEY}"
  host: "https://cloud.langfuse.com"
  sampling_rate: 1.0  # 100% 采样
  mask_inputs: false
  mask_outputs: false
```

#### 生产环境

```yaml
langfuse:
  enabled: true
  public_key: "${LANGFUSE_PUBLIC_KEY}"
  secret_key: "${LANGFUSE_SECRET_KEY}"
  host: "https://langfuse.example.com"  # 自托管
  sampling_rate: 0.1  # 10% 采样（降低成本）
  mask_inputs: true   # 脱敏输入
  mask_outputs: true  # 脱敏输出
  custom_mask_patterns:
    - "\\b[A-Z0-9]{32}\\b"  # API tokens
```

#### 禁用 Langfuse

```yaml
langfuse:
  enabled: false
```

## 部署考虑

### 1. Langfuse Server 选择

#### 云端服务（推荐用于快速开始）

- **优点**：
  - 无需维护基础设施
  - 自动扩展
  - 内置备份和高可用
  - 快速开始

- **缺点**：
  - 数据存储在第三方
  - 可能有数据传输成本
  - 依赖外部服务可用性

- **适用场景**：
  - 开发和测试环境
  - 小规模生产环境
  - 对数据隐私要求不高的场景

#### 自托管（推荐用于生产环境）

- **优点**：
  - 完全控制数据
  - 无数据传输成本
  - 可定制化
  - 符合数据合规要求

- **缺点**：
  - 需要维护基础设施
  - 需要配置高可用和备份
  - 初始设置复杂

- **适用场景**：
  - 生产环境
  - 对数据隐私要求高的场景
  - 大规模部署

### 2. 自托管部署

#### Docker Compose 部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  langfuse-server:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://langfuse:password@postgres:5432/langfuse
      - NEXTAUTH_URL=https://langfuse.example.com
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=langfuse
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

#### Kubernetes 部署

```yaml
# langfuse-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
spec:
  replicas: 3
  selector:
    matchLabels:
      app: langfuse
  template:
    metadata:
      labels:
        app: langfuse
    spec:
      containers:
      - name: langfuse
        image: langfuse/langfuse:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: database-url
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: nextauth-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: langfuse
spec:
  selector:
    app: langfuse
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

### 3. 网络配置

#### 防火墙规则

```bash
# 允许 OwlClaw Agent 访问 Langfuse Server
# 假设 Agent 在 10.0.1.0/24，Langfuse 在 10.0.2.10

iptables -A INPUT -s 10.0.1.0/24 -d 10.0.2.10 -p tcp --dport 3000 -j ACCEPT
```

#### TLS/SSL 配置

使用 Nginx 作为反向代理，配置 HTTPS：

```nginx
# /etc/nginx/sites-available/langfuse

server {
    listen 443 ssl http2;
    server_name langfuse.example.com;

    ssl_certificate /etc/letsencrypt/live/langfuse.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/langfuse.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 性能优化

#### 连接池配置

```python
# 使用连接池复用 HTTP 连接

from langfuse import Langfuse
import httpx

# 创建自定义 HTTP 客户端
http_client = httpx.Client(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
    ),
    timeout=httpx.Timeout(10.0),
)

# 使用自定义客户端初始化 Langfuse
langfuse = Langfuse(
    public_key=config.public_key,
    secret_key=config.secret_key,
    host=config.host,
    httpx_client=http_client,
)
```

#### 批量上报

```python
# 配置批量上报参数

langfuse = Langfuse(
    public_key=config.public_key,
    secret_key=config.secret_key,
    host=config.host,
    flush_at=10,  # 累积 10 个事件后上报
    flush_interval=5,  # 或每 5 秒上报一次
)
```

#### 采样策略

```python
# 根据环境动态调整采样率

def get_sampling_rate() -> float:
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'development':
        return 1.0  # 100% 采样
    elif env == 'staging':
        return 0.5  # 50% 采样
    elif env == 'production':
        return 0.1  # 10% 采样
    else:
        return 0.01  # 1% 采样
```

### 5. 监控和告警

#### 监控指标

- **Langfuse 可用性**：定期检查 Langfuse Server 是否可访问
- **上报成功率**：监控 trace 上报的成功率
- **上报延迟**：监控 trace 上报的延迟
- **队列大小**：监控待上报的 trace 队列大小

#### Prometheus 指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
langfuse_traces_created = Counter(
    'langfuse_traces_created_total',
    'Total number of traces created',
)

langfuse_traces_failed = Counter(
    'langfuse_traces_failed_total',
    'Total number of traces that failed to create',
)

langfuse_upload_duration = Histogram(
    'langfuse_upload_duration_seconds',
    'Time spent uploading traces to Langfuse',
)

langfuse_queue_size = Gauge(
    'langfuse_queue_size',
    'Number of traces waiting to be uploaded',
)

# 在代码中使用
def create_trace(self, name: str, metadata: TraceMetadata) -> Optional[str]:
    try:
        trace = self._client.trace(name=name, metadata=metadata)
        langfuse_traces_created.inc()
        return trace.id
    except Exception as e:
        langfuse_traces_failed.inc()
        logger.warning(f"Failed to create trace: {e}")
        return None
```

#### 告警规则

```yaml
# prometheus-alerts.yaml

groups:
- name: langfuse
  rules:
  - alert: LangfuseHighFailureRate
    expr: rate(langfuse_traces_failed_total[5m]) / rate(langfuse_traces_created_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Langfuse trace creation failure rate is high"
      description: "{{ $value | humanizePercentage }} of traces are failing to create"

  - alert: LangfuseQueueBacklog
    expr: langfuse_queue_size > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Langfuse upload queue is backing up"
      description: "{{ $value }} traces are waiting to be uploaded"
```

### 6. 数据保留和清理

#### Langfuse 数据保留策略

在 Langfuse UI 中配置数据保留策略：

- **开发环境**：保留 7 天
- **测试环境**：保留 30 天
- **生产环境**：保留 90 天

#### 定期清理

```sql
-- 清理 90 天前的 trace 数据

DELETE FROM traces
WHERE timestamp < NOW() - INTERVAL '90 days';

-- 清理孤立的 observations (spans)

DELETE FROM observations
WHERE trace_id NOT IN (SELECT id FROM traces);
```

### 7. 安全考虑

#### API Key 管理

- 使用环境变量或密钥管理服务（如 AWS Secrets Manager、HashiCorp Vault）存储 API key
- 定期轮换 API key
- 为不同环境使用不同的 API key
- 限制 API key 的权限（只读 vs 读写）

#### 网络安全

- 使用 HTTPS 传输数据
- 配置防火墙规则，只允许必要的网络访问
- 使用 VPN 或专用网络连接 Langfuse Server
- 启用 IP 白名单（如果 Langfuse 支持）

#### 数据脱敏

- 在生产环境启用输入和输出脱敏
- 配置自定义脱敏规则以匹配业务需求
- 定期审查脱敏规则的有效性
- 对敏感字段（如密码、API key）进行额外保护

### 8. 灾难恢复

#### 备份策略

```bash
# 备份 Langfuse PostgreSQL 数据库

pg_dump -h localhost -U langfuse -d langfuse > langfuse_backup_$(date +%Y%m%d).sql

# 压缩备份

gzip langfuse_backup_$(date +%Y%m%d).sql

# 上传到 S3

aws s3 cp langfuse_backup_$(date +%Y%m%d).sql.gz s3://backups/langfuse/
```

#### 恢复流程

```bash
# 从备份恢复

gunzip langfuse_backup_20240115.sql.gz
psql -h localhost -U langfuse -d langfuse < langfuse_backup_20240115.sql
```

#### 高可用配置

- 使用 PostgreSQL 主从复制
- 配置 Langfuse Server 多副本（Kubernetes）
- 使用负载均衡器分发请求
- 配置健康检查和自动故障转移

## 迁移和兼容性

### 从无可观测性迁移

如果现有系统没有可观测性，迁移步骤：

1. **添加依赖**：安装 Langfuse Python SDK
2. **添加配置**：在配置文件中添加 Langfuse 配置
3. **初始化客户端**：在 Agent Runtime 中初始化 LangfuseClient
4. **测试**：在开发环境测试 trace 创建
5. **灰度发布**：使用采样率逐步增加上报量
6. **全量发布**：将采样率设置为 1.0

### 从其他可观测性平台迁移

如果现有系统使用其他可观测性平台（如 OpenTelemetry、Datadog），迁移步骤：

1. **并行运行**：同时运行 Langfuse 和现有平台
2. **对比数据**：验证 Langfuse 数据的准确性
3. **逐步切换**：逐步将流量从现有平台切换到 Langfuse
4. **完全切换**：停用现有平台

### 版本兼容性

- **Langfuse Python SDK**：支持 Python 3.8+
- **Langfuse Server**：建议使用最新稳定版
- **向后兼容**：Langfuse SDK 保证向后兼容，升级不会破坏现有代码

## 成本估算

### Langfuse 云端服务定价

（假设定价，实际以 Langfuse 官网为准）

- **免费层**：每月 10,000 traces
- **专业版**：$99/月，每月 100,000 traces
- **企业版**：自定义定价，无限 traces

### 自托管成本

- **服务器成本**：$50-200/月（取决于规模）
- **数据库成本**：$20-100/月（PostgreSQL）
- **存储成本**：$10-50/月（取决于数据保留策略）
- **运维成本**：需要专人维护

### 成本优化建议

1. **使用采样**：在生产环境使用 10-20% 采样率
2. **缩短保留期**：只保留必要的数据（如 30-90 天）
3. **自托管**：大规模使用时自托管更经济
4. **按需启用**：只在需要调试时启用 100% 采样

## 总结

Langfuse 集成为 OwlClaw Agent 提供了强大的可观测性能力，使得开发者能够：

1. **追踪决策过程**：查看 Agent 每次 run 的完整 LLM 调用链
2. **分析成本**：精确统计 token 使用量和成本
3. **监控性能**：监控 LLM 调用延迟和成功率
4. **评估质量**：支持人工标注和自动评分

通过隔离设计、异步上报、优雅降级和隐私保护，该集成在提供强大功能的同时，保持了系统的稳定性和安全性。


