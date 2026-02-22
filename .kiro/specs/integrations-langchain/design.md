# 设计文档：LangChain 集成

## 概述

本文档描述了将 LangChain 编排框架集成到 OwlClaw Agent 系统的设计。该集成提供适配层，使 LangChain 的 Runnable（chain、tool、graph）可以作为 OwlClaw capability 注册，并受治理层、Ledger 和可观测体系约束。

该集成遵循隔离设计模式，所有 LangChain 相关代码集中在 `owlclaw/integrations/langchain/` 目录中，使得未来替换或支持其他编排框架变得容易。

### 核心设计原则

1. **可选依赖**：LangChain 作为可选依赖，不影响核心 SDK
2. **隔离性**：所有 LangChain 逻辑隔离在独立模块中
3. **透明集成**：对用户透明，注册后的 Runnable 像普通 capability 一样使用
4. **治理一致**：LangChain 执行受相同的治理和审计约束
5. **最小侵入**：自动处理转换和追踪，无需手动埋点

### 设计目标

- 提供简洁的 API 注册 LangChain Runnable 为 capability
- 自动处理输入输出的 schema 验证和转换
- 集成 Governance Layer 进行权限控制
- 集成 Ledger 进行执行记录和审计
- 集成 Langfuse 进行可观测性追踪
- 提供完善的错误处理和降级机制

## 架构

### 系统上下文

```
┌─────────────────────────────────────────────────────────────┐
│                    OwlClaw Agent System                      │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Capabilities │    │  Governance  │    │    Ledger    │  │
│  │   Registry   │    │    Layer     │    │              │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                    │           │
│         └───────────────────┼────────────────────┘           │
│                             │                                │
│         ┌───────────────────▼────────────────────┐           │
│         │   LangChain Integration Layer          │           │
│         │  ┌──────────────────────────────────┐  │           │
│         │  │  LangChainAdapter                │  │           │
│         │  │  - Schema Validation             │  │           │
│         │  │  - Input/Output Transformation   │  │           │
│         │  │  - Error Handling                │  │           │
│         │  │  - Trace Management              │  │           │
│         │  └──────────────────────────────────┘  │           │
│         └───────────────────┬────────────────────┘           │
│                             │                                │
└─────────────────────────────┼────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  LangChain SDK   │
                    │  - Runnables     │
                    │  - Chains        │
                    │  - Graphs        │
                    └──────────────────┘
```

### 集成边界

**OwlClaw 组件：**
- Capabilities Registry：能力注册和管理
- Governance Layer：权限控制和策略执行
- Ledger：执行记录和审计
- Langfuse Integration：可观测性追踪

**LangChain 组件：**
- Runnable Interface：统一的执行接口
- Chains：链式调用
- Graphs：图结构工作流
- Tools：工具集成

**适配层职责：**
- 封装 LangChain Runnable 为 OwlClaw capability handler
- 处理 schema 验证和数据转换
- 集成治理层和 Ledger
- 管理 trace 上下文
- 处理错误和降级

### 数据流

```
Capability Call
    │
    ▼
┌─────────────────────────────────────┐
│  1. Governance Layer Validation     │
│     - Check permissions             │
│     - Apply rate limits             │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  2. Input Schema Validation         │
│     - Validate against JSON Schema  │
│     - Return 400 if invalid         │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  3. Input Transformation            │
│     - Convert OwlClaw → LangChain   │
│     - Apply custom transformers     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  4. Runnable Execution              │
│     - Create trace span             │
│     - Execute Runnable              │
│     - Handle errors                 │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  5. Output Transformation           │
│     - Convert LangChain → OwlClaw   │
│     - Apply custom transformers     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  6. Ledger Recording                │
│     - Record execution details      │
│     - Record success/failure        │
└─────────────┬───────────────────────┘
              │
              ▼
         Return Result
```

### 组件架构

```
owlclaw/integrations/langchain/
├─ __init__.py
├─ adapter.py (LangChainAdapter)
│  ├─ register_runnable()
│  ├─ create_handler()
│  └─ execute()
│
├─ schema.py (SchemaBridge)
│  ├─ validate_input()
│  ├─ transform_input()
│  └─ transform_output()
│
├─ errors.py (Error Handling)
│  ├─ map_exception()
│  ├─ create_error_response()
│  └─ handle_fallback()
│
├─ trace.py (Trace Management)
│  ├─ create_span()
│  ├─ record_execution()
│  └─ integrate_langfuse()
│
└─ config.py (Configuration)
   ├─ LangChainConfig
   ├─ load_config()
   └─ validate_config()
```

## 组件和接口

### 1. LangChainAdapter

主适配器类，负责将 LangChain Runnable 包装为 OwlClaw capability handler。

#### 接口定义

```python
from typing import Optional, Dict, Any, Callable, Union
from dataclasses import dataclass
from langchain.schema.runnable import Runnable

@dataclass
class RunnableConfig:
    """Runnable 配置"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    
    # 转换器
    input_transformer: Optional[Callable] = None
    output_transformer: Optional[Callable] = None
    
    # 错误处理
    fallback: Optional[str] = None  # fallback capability name
    retry_policy: Optional[Dict[str, Any]] = None
    
    # 超时配置
    timeout_seconds: Optional[int] = None
    
    # 追踪配置
    enable_tracing: bool = True

class LangChainAdapter:
    """LangChain 适配器"""
    
    def __init__(
        self,
        app: 'OwlClawApp',
        config: 'LangChainConfig'
    ):
        """
        初始化适配器
        
        Args:
            app: OwlClaw 应用实例
            config: LangChain 配置
        """
        self.app = app
        self.config = config
        self._schema_bridge = SchemaBridge()
        self._trace_manager = TraceManager(config)
        self._error_handler = ErrorHandler(config)
    
    def register_runnable(
        self,
        runnable: Runnable,
        config: RunnableConfig
    ) -> None:
        """
        注册 Runnable 为 capability
        
        Args:
            runnable: LangChain Runnable 实例
            config: Runnable 配置
        """
        # 验证 Runnable 类型
        if not isinstance(runnable, Runnable):
            raise TypeError(f"Expected Runnable, got {type(runnable)}")
        
        # 创建 capability handler
        handler = self._create_handler(runnable, config)
        
        # 注册到 capabilities registry
        self.app.register_capability(
            name=config.name,
            handler=handler,
            description=config.description,
            input_schema=config.input_schema,
            output_schema=config.output_schema
        )
    
    def _create_handler(
        self,
        runnable: Runnable,
        config: RunnableConfig
    ) -> Callable:
        """
        创建 capability handler
        
        Args:
            runnable: LangChain Runnable
            config: Runnable 配置
        
        Returns:
            Capability handler 函数
        """
        async def handler(input: Dict[str, Any], context: 'ExecutionContext') -> Dict[str, Any]:
            return await self.execute(runnable, input, context, config)
        
        return handler
    
    async def execute(
        self,
        runnable: Runnable,
        input: Dict[str, Any],
        context: 'ExecutionContext',
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """
        执行 Runnable
        
        Args:
            runnable: LangChain Runnable
            input: 输入数据
            context: 执行上下文
            config: Runnable 配置
        
        Returns:
            执行结果
        """
        # 1. 验证输入 schema
        try:
            self._schema_bridge.validate_input(input, config.input_schema)
        except ValidationError as e:
            return self._error_handler.create_error_response(
                error_type="ValidationError",
                message=str(e),
                status_code=400
            )
        
        # 2. 转换输入
        transformed_input = self._schema_bridge.transform_input(
            input,
            config.input_transformer
        )
        
        # 3. 创建 trace span
        span = None
        if config.enable_tracing:
            span = self._trace_manager.create_span(
                name=f"langchain_{config.name}",
                input=transformed_input,
                context=context
            )
        
        # 4. 执行 Runnable
        try:
            result = await self._execute_with_timeout(
                runnable,
                transformed_input,
                config.timeout_seconds
            )
        except Exception as e:
            # 记录错误
            if span:
                span.record_error(e)
            
            # 尝试 fallback
            if config.fallback:
                return await self._error_handler.handle_fallback(
                    config.fallback,
                    input,
                    context,
                    error=e
                )
            
            # 映射异常
            return self._error_handler.map_exception(e)
        
        # 5. 转换输出
        transformed_output = self._schema_bridge.transform_output(
            result,
            config.output_transformer
        )
        
        # 6. 结束 span
        if span:
            span.end(output=transformed_output)
        
        return transformed_output
    
    async def _execute_with_timeout(
        self,
        runnable: Runnable,
        input: Dict[str, Any],
        timeout_seconds: Optional[int]
    ) -> Any:
        """
        带超时的执行
        
        Args:
            runnable: LangChain Runnable
            input: 输入数据
            timeout_seconds: 超时时间（秒）
        
        Returns:
            执行结果
        """
        import asyncio
        
        # 检测 Runnable 是否支持异步
        if hasattr(runnable, 'ainvoke'):
            coro = runnable.ainvoke(input)
        else:
            # 同步 Runnable，在 executor 中运行
            loop = asyncio.get_event_loop()
            coro = loop.run_in_executor(None, runnable.invoke, input)
        
        # 应用超时
        if timeout_seconds:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        else:
            return await coro
```

### 2. SchemaBridge

Schema 验证和数据转换组件。

```python
from jsonschema import validate, ValidationError as JSONSchemaValidationError
from typing import Dict, Any, Optional, Callable

class ValidationError(Exception):
    """Schema 验证错误"""
    pass

class SchemaBridge:
    """Schema 桥接器"""
    
    def validate_input(
        self,
        input: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> None:
        """
        验证输入是否符合 schema
        
        Args:
            input: 输入数据
            schema: JSON Schema
        
        Raises:
            ValidationError: 验证失败
        """
        try:
            validate(instance=input, schema=schema)
        except JSONSchemaValidationError as e:
            raise ValidationError(f"Input validation failed: {e.message}")
    
    def transform_input(
        self,
        input: Dict[str, Any],
        transformer: Optional[Callable] = None
    ) -> Any:
        """
        转换输入数据
        
        Args:
            input: 原始输入
            transformer: 自定义转换函数
        
        Returns:
            转换后的输入
        """
        if transformer:
            return transformer(input)
        
        # 默认转换：保持原样
        return input
    
    def transform_output(
        self,
        output: Any,
        transformer: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        转换输出数据
        
        Args:
            output: Runnable 输出
            transformer: 自定义转换函数
        
        Returns:
            转换后的输出
        """
        if transformer:
            return transformer(output)
        
        # 默认转换：包装为字典
        if isinstance(output, dict):
            return output
        else:
            return {"result": output}
```

### 3. ErrorHandler

错误处理和映射组件。

```python
from typing import Dict, Any, Optional, Type
import logging

logger = logging.getLogger(__name__)

class ErrorHandler:
    """错误处理器"""
    
    # 异常映射表
    EXCEPTION_MAPPING = {
        "ValueError": ("ValidationError", 400),
        "TimeoutError": ("TimeoutError", 504),
        "RateLimitError": ("RateLimitError", 429),
        "APIError": ("ExternalServiceError", 502),
        "Exception": ("InternalError", 500),
    }
    
    def __init__(self, config: 'LangChainConfig'):
        self.config = config
    
    def map_exception(self, exception: Exception) -> Dict[str, Any]:
        """
        映射异常为 OwlClaw 错误响应
        
        Args:
            exception: 原始异常
        
        Returns:
            错误响应
        """
        # 获取异常类型名称
        exception_type = type(exception).__name__
        
        # 查找映射
        error_type, status_code = self.EXCEPTION_MAPPING.get(
            exception_type,
            self.EXCEPTION_MAPPING["Exception"]
        )
        
        # 记录错误
        logger.error(
            f"LangChain execution failed: {exception_type}: {str(exception)}",
            exc_info=True
        )
        
        return self.create_error_response(
            error_type=error_type,
            message=str(exception),
            status_code=status_code,
            details={"original_exception": exception_type}
        )
    
    def create_error_response(
        self,
        error_type: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            error_type: 错误类型
            message: 错误消息
            status_code: HTTP 状态码
            details: 额外详情
        
        Returns:
            错误响应
        """
        return {
            "error": {
                "type": error_type,
                "message": message,
                "status_code": status_code,
                "details": details or {}
            }
        }
    
    async def handle_fallback(
        self,
        fallback_name: str,
        input: Dict[str, Any],
        context: 'ExecutionContext',
        error: Exception
    ) -> Dict[str, Any]:
        """
        处理 fallback
        
        Args:
            fallback_name: Fallback capability 名称
            input: 原始输入
            context: 执行上下文
            error: 原始错误
        
        Returns:
            Fallback 执行结果
        """
        logger.warning(
            f"Primary handler failed, executing fallback: {fallback_name}",
            extra={"error": str(error)}
        )
        
        # 调用 fallback capability
        try:
            result = await context.app.execute_capability(
                name=fallback_name,
                input=input,
                context=context
            )
            
            # 标记使用了 fallback
            result["_fallback_used"] = True
            result["_primary_error"] = str(error)
            
            return result
        except Exception as fallback_error:
            logger.error(
                f"Fallback also failed: {fallback_name}",
                exc_info=True
            )
            
            # 返回原始错误
            return self.map_exception(error)
```

### 4. TraceManager

Trace 管理和 Langfuse 集成组件。

```python
from typing import Dict, Any, Optional
from owlclaw.integrations.langfuse import TraceContext
import time

class TraceSpan:
    """Trace Span"""
    
    def __init__(
        self,
        name: str,
        trace_id: str,
        parent_span_id: Optional[str],
        input: Dict[str, Any]
    ):
        self.name = name
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.input = input
        self.start_time = time.time()
        self.output: Optional[Dict[str, Any]] = None
        self.error: Optional[Exception] = None
        self.duration_ms: Optional[float] = None
    
    def end(self, output: Optional[Dict[str, Any]] = None) -> None:
        """结束 span"""
        self.output = output
        self.duration_ms = (time.time() - self.start_time) * 1000
    
    def record_error(self, error: Exception) -> None:
        """记录错误"""
        self.error = error
        self.duration_ms = (time.time() - self.start_time) * 1000

class TraceManager:
    """Trace 管理器"""
    
    def __init__(self, config: 'LangChainConfig'):
        self.config = config
    
    def create_span(
        self,
        name: str,
        input: Dict[str, Any],
        context: 'ExecutionContext'
    ) -> TraceSpan:
        """
        创建 trace span
        
        Args:
            name: Span 名称
            input: 输入数据
            context: 执行上下文
        
        Returns:
            Trace span
        """
        # 获取当前 trace context
        trace_ctx = TraceContext.get_current()
        
        if not trace_ctx:
            # 没有 trace context，创建新的
            trace_id = self._generate_trace_id()
            parent_span_id = None
        else:
            trace_id = trace_ctx.trace_id
            parent_span_id = trace_ctx.parent_span_id
        
        # 创建 span
        span = TraceSpan(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            input=input
        )
        
        # 如果启用 Langfuse，创建 Langfuse span
        if self.config.tracing.langfuse_integration:
            self._create_langfuse_span(span, context)
        
        return span
    
    def _create_langfuse_span(
        self,
        span: TraceSpan,
        context: 'ExecutionContext'
    ) -> None:
        """创建 Langfuse span"""
        from owlclaw.integrations.langfuse import LangfuseClient
        
        # 获取 Langfuse 客户端
        langfuse = context.app.langfuse
        
        if langfuse:
            langfuse.create_span(
                trace_id=span.trace_id,
                name=span.name,
                input=span.input,
                parent_span_id=span.parent_span_id
            )
    
    def _generate_trace_id(self) -> str:
        """生成 trace ID"""
        import uuid
        return f"trace_{uuid.uuid4().hex[:16]}"
```

### 5. LangChainConfig

配置管理组件。

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import yaml
import os

@dataclass
class TracingConfig:
    """追踪配置"""
    enabled: bool = True
    langfuse_integration: bool = True

@dataclass
class PrivacyConfig:
    """隐私配置"""
    mask_inputs: bool = False
    mask_outputs: bool = False
    mask_patterns: List[str] = field(default_factory=list)

@dataclass
class LangChainConfig:
    """LangChain 配置"""
    enabled: bool = True
    
    # 版本验证
    version_check: bool = True
    min_version: str = "0.1.0"
    max_version: str = "0.3.0"
    
    # 执行配置
    default_timeout_seconds: int = 30
    max_concurrent_executions: int = 10
    
    # 追踪配置
    tracing: TracingConfig = field(default_factory=TracingConfig)
    
    # 隐私配置
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'LangChainConfig':
        """
        从 YAML 文件加载配置
        
        Args:
            path: 配置文件路径
        
        Returns:
            配置对象
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # 替换环境变量
        data = cls._replace_env_vars(data)
        
        # 提取 langchain 配置
        langchain_config = data.get('langchain', {})
        
        return cls(
            enabled=langchain_config.get('enabled', True),
            version_check=langchain_config.get('version_check', True),
            min_version=langchain_config.get('min_version', '0.1.0'),
            max_version=langchain_config.get('max_version', '0.3.0'),
            default_timeout_seconds=langchain_config.get('default_timeout_seconds', 30),
            max_concurrent_executions=langchain_config.get('max_concurrent_executions', 10),
            tracing=TracingConfig(**langchain_config.get('tracing', {})),
            privacy=PrivacyConfig(**langchain_config.get('privacy', {}))
        )
    
    @staticmethod
    def _replace_env_vars(data: Any) -> Any:
        """
        替换配置中的环境变量
        
        Args:
            data: 配置数据
        
        Returns:
            替换后的数据
        """
        if isinstance(data, str):
            # 替换 ${VAR_NAME} 格式的环境变量
            import re
            pattern = r'\$\{([^}]+)\}'
            
            def replacer(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            
            return re.sub(pattern, replacer, data)
        elif isinstance(data, dict):
            return {k: LangChainConfig._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [LangChainConfig._replace_env_vars(item) for item in data]
        else:
            return data
    
    def validate(self) -> None:
        """
        验证配置的合法性
        
        Raises:
            ValueError: 配置无效
        """
        # 验证超时时间
        if self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive")
        
        # 验证并发数
        if self.max_concurrent_executions <= 0:
            raise ValueError("max_concurrent_executions must be positive")
        
        # 验证版本范围
        if self.version_check:
            from packaging import version
            if version.parse(self.min_version) >= version.parse(self.max_version):
                raise ValueError("min_version must be less than max_version")
```

## 数据模型

### Capability 注册数据

```python
{
    "name": "summarize",
    "description": "Summarize text using LangChain",
    "type": "langchain_runnable",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to summarize"
            }
        },
        "required": ["text"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Generated summary"
            }
        }
    },
    "config": {
        "timeout_seconds": 30,
        "enable_tracing": true,
        "fallback": "summarize_simple"
    }
}
```

### 执行记录数据

```python
{
    "event_type": "langchain_execution",
    "capability_name": "summarize",
    "runnable_type": "LLMChain",
    "input": {
        "text": "Long text to summarize..."
    },
    "output": {
        "summary": "Brief summary..."
    },
    "status": "success",
    "duration_ms": 1234,
    "error_message": null,
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": "user_123",
    "agent_id": "agent_001",
    "trace_id": "trace_abc123",
    "span_id": "span_xyz789"
}
```

### Trace Span 数据

```python
{
    "span_id": "span_xyz789",
    "trace_id": "trace_abc123",
    "parent_span_id": "span_parent",
    "name": "langchain_summarize",
    "type": "langchain_execution",
    "start_time": "2024-01-15T10:30:00.000Z",
    "end_time": "2024-01-15T10:30:01.234Z",
    "duration_ms": 1234,
    "input": {
        "text": "Long text..."
    },
    "output": {
        "summary": "Brief summary..."
    },
    "metadata": {
        "runnable_type": "LLMChain",
        "capability_name": "summarize",
        "execution_mode": "async"
    },
    "status": "success",
    "error": null
}
```

## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：Runnable 类型验证

*对于任意*对象，当尝试注册为 capability 时，如果该对象不是有效的 LangChain Runnable 类型，系统应该拒绝注册并抛出 TypeError。

**验证需求：FR-3.4**

### 属性 2：注册失败错误信息

*对于任意*无效的注册尝试（无效类型、缺少必需字段、schema 格式错误），系统应该抛出包含详细错误信息的异常，说明失败原因。

**验证需求：FR-3.5**

### 属性 3：输入 Schema 验证

*对于任意*输入数据和 JSON Schema，系统应该正确验证输入是否符合 schema，符合则通过，不符合则拒绝。

**验证需求：FR-5.1**

### 属性 4：Schema 验证失败响应

*对于任意*不符合 schema 的输入，系统应该返回 400 错误响应，并包含具体的验证失败原因。

**验证需求：FR-5.3**

### 属性 5：输出格式封装

*对于任意*Runnable 输出（字符串、数字、对象、数组），系统应该将其封装为标准的 OwlClaw result 格式（字典类型）。

**验证需求：FR-6.2**

### 属性 6：异步检测

*对于任意*Runnable，系统应该能够正确检测其是否支持异步执行（是否有 ainvoke 方法），并选择合适的调用方式。

**验证需求：FR-7.1**

### 属性 7：权限验证失败响应

*对于任意*权限验证失败的执行请求，系统应该返回 403 错误响应，并包含拒绝原因。

**验证需求：FR-9.3**

### 属性 8：执行记录完整性

*对于任意*LangChain 执行（无论成功或失败），系统应该在 Ledger 中创建一条记录，包含执行状态、时长、输入输出等信息。

**验证需求：FR-11.1, FR-11.2**

### 属性 9：Trace Span 创建

*对于任意*启用追踪的 LangChain 执行，系统应该创建独立的 trace span，包含 span 名称、输入、输出、时长等信息。

**验证需求：FR-13.1**

### 属性 10：异常捕获

*对于任意*LangChain Runnable 抛出的异常，系统应该捕获该异常，不让其传播到上层导致系统崩溃。

**验证需求：FR-16.1**

### 属性 11：异常映射

*对于任意*LangChain 异常，系统应该将其映射为对应的 OwlClaw 错误类型，并返回适当的 HTTP 状态码。

**验证需求：FR-16.2**

### 属性 12：指数退避重试

*对于任意*配置了重试策略的执行，当发生可重试错误时，系统应该使用指数退避算法计算重试延迟，每次重试的延迟应该是前一次的倍数。

**验证需求：FR-18.4**

### 属性 13：PII 脱敏

*对于任意*包含 PII（邮箱、电话号码）的数据，当启用隐私保护时，系统应该自动检测并脱敏这些信息，替换为脱敏标记。

**验证需求：NFR-5.2**

## 错误处理

### 错误类型和映射

| LangChain 异常 | OwlClaw 错误类型 | HTTP 状态码 | 说明 |
|---------------|-----------------|------------|------|
| ValueError | ValidationError | 400 | 输入验证失败 |
| TimeoutError | TimeoutError | 504 | 执行超时 |
| RateLimitError | RateLimitError | 429 | 速率限制 |
| APIError | ExternalServiceError | 502 | 外部服务错误 |
| Exception | InternalError | 500 | 内部错误 |

### 错误处理流程

```
Runnable Execution
    │
    ├─ Success → Transform Output → Return Result
    │
    └─ Exception
        │
        ├─ Capture Exception
        │
        ├─ Map to OwlClaw Error
        │
        ├─ Record to Ledger
        │
        ├─ Check Fallback
        │   │
        │   ├─ Has Fallback → Execute Fallback
        │   │
        │   └─ No Fallback → Return Error
        │
        └─ Check Retry Policy
            │
            ├─ Retryable → Retry with Backoff
            │
            └─ Not Retryable → Return Error
```

### Fallback 机制

```python
# 配置 fallback
@app.handler(
    name="summarize",
    fallback="summarize_simple"
)
def summarize_handler(input: dict) -> dict:
    # 主处理逻辑
    chain = create_complex_chain()
    return chain.invoke(input)

# Fallback handler
@app.handler(name="summarize_simple")
def summarize_simple_handler(input: dict) -> dict:
    # 简单的降级逻辑
    text = input["text"]
    return {"summary": text[:100] + "..."}
```

### 重试策略

```python
# 配置重试策略
@app.handler(
    name="summarize",
    retry_policy={
        "max_attempts": 3,
        "initial_delay_ms": 100,
        "max_delay_ms": 5000,
        "backoff_multiplier": 2.0,
        "retryable_errors": ["TimeoutError", "RateLimitError"]
    }
)
def summarize_handler(input: dict) -> dict:
    # 处理逻辑
    ...
```

**重试延迟计算**：
```
delay = min(initial_delay * (backoff_multiplier ^ attempt), max_delay)

示例（initial_delay=100ms, multiplier=2.0, max_delay=5000ms）：
- Attempt 1: 100ms
- Attempt 2: 200ms
- Attempt 3: 400ms
- Attempt 4: 800ms
- Attempt 5: 1600ms
- Attempt 6: 3200ms
- Attempt 7: 5000ms (capped)
```

## 测试策略

### 单元测试

**测试范围**：
- Schema 验证逻辑
- 输入输出转换
- 异常映射
- 配置加载和验证
- Trace span 创建

**测试工具**：
- pytest：测试框架
- pytest-asyncio：异步测试支持
- pytest-mock：Mock 支持

**示例测试**：
```python
def test_schema_validation_success():
    """测试 schema 验证成功"""
    bridge = SchemaBridge()
    input_data = {"text": "Hello world"}
    schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
    }
    
    # 应该不抛出异常
    bridge.validate_input(input_data, schema)

def test_schema_validation_failure():
    """测试 schema 验证失败"""
    bridge = SchemaBridge()
    input_data = {"text": 123}  # 错误类型
    schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
    }
    
    # 应该抛出 ValidationError
    with pytest.raises(ValidationError):
        bridge.validate_input(input_data, schema)
```

### 属性测试

**测试范围**：
- 输入验证对所有输入的正确性
- 输出转换对所有输出的正确性
- 异常映射对所有异常的正确性
- 重试延迟计算的正确性

**测试工具**：
- hypothesis：属性测试框架

**示例测试**：
```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.integers()))
def test_output_transformation_always_returns_dict(output):
    """属性：输出转换总是返回字典"""
    bridge = SchemaBridge()
    result = bridge.transform_output(output)
    assert isinstance(result, dict)

@given(
    st.integers(min_value=1, max_value=10),
    st.integers(min_value=100, max_value=1000),
    st.floats(min_value=1.5, max_value=3.0)
)
def test_exponential_backoff_increases(attempt, initial_delay, multiplier):
    """属性：指数退避延迟递增"""
    delay1 = calculate_backoff_delay(attempt, initial_delay, multiplier, 10000)
    delay2 = calculate_backoff_delay(attempt + 1, initial_delay, multiplier, 10000)
    assert delay2 >= delay1
```

### 集成测试

**测试范围**：
- 完整的 Runnable 注册和执行流程
- 与 Governance Layer 的集成
- 与 Ledger 的集成
- 与 Langfuse 的集成
- Fallback 机制
- 重试机制

**测试场景**：
1. 注册简单 LLMChain 并执行
2. 注册复杂 SequentialChain 并执行
3. 执行失败触发 fallback
4. 执行失败触发重试
5. 权限验证失败
6. Schema 验证失败
7. 超时处理

**示例测试**：
```python
@pytest.mark.asyncio
async def test_runnable_execution_with_governance():
    """测试 Runnable 执行与治理层集成"""
    # 创建 mock Runnable
    mock_runnable = create_mock_runnable()
    
    # 注册
    adapter = LangChainAdapter(app, config)
    adapter.register_runnable(
        runnable=mock_runnable,
        config=RunnableConfig(
            name="test_chain",
            description="Test chain",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}}
        )
    )
    
    # 执行
    result = await app.execute_capability(
        name="test_chain",
        input={"text": "Hello"},
        context=create_test_context()
    )
    
    # 验证
    assert result["status"] == "success"
    assert "output" in result
    
    # 验证 Governance Layer 被调用
    assert governance_layer.validate_called
    
    # 验证 Ledger 记录
    assert ledger.has_record("test_chain")
```

### 端到端测试

**测试范围**：
- 从安装到执行的完整流程
- 真实 LangChain Runnable 的执行
- 真实 Langfuse 集成

**测试场景**：
1. 安装 owlclaw[langchain]
2. 创建真实的 LLMChain
3. 注册并执行
4. 验证 Langfuse 中的 trace
5. 验证 Ledger 中的记录

## 配置示例

### 基础配置

```yaml
# config/langchain.yaml
langchain:
  enabled: true
  
  # 版本验证
  version_check: true
  min_version: "0.1.0"
  max_version: "0.3.0"
  
  # 执行配置
  default_timeout_seconds: 30
  max_concurrent_executions: 10
  
  # 追踪配置
  tracing:
    enabled: true
    langfuse_integration: true
  
  # 隐私配置
  privacy:
    mask_inputs: false
    mask_outputs: false
    mask_patterns:
      - "api_key"
      - "password"
      - "secret"
```

### 环境变量配置

```bash
# .env
OWLCLAW_LANGCHAIN_ENABLED=true
OWLCLAW_LANGCHAIN_TIMEOUT=30
OWLCLAW_LANGCHAIN_TRACING_ENABLED=true
OWLCLAW_LANGCHAIN_LANGFUSE_INTEGRATION=true
```

### 使用环境变量的配置

```yaml
# config/langchain.yaml
langchain:
  enabled: ${OWLCLAW_LANGCHAIN_ENABLED}
  default_timeout_seconds: ${OWLCLAW_LANGCHAIN_TIMEOUT}
  
  tracing:
    enabled: ${OWLCLAW_LANGCHAIN_TRACING_ENABLED}
    langfuse_integration: ${OWLCLAW_LANGCHAIN_LANGFUSE_INTEGRATION}
```

## 使用示例

### 示例 1：注册简单 LLMChain

```python
from owlclaw import OwlClawApp
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

app = OwlClawApp()

# 创建 LLMChain
llm = OpenAI(temperature=0.7)
prompt = PromptTemplate(
    input_variables=["text"],
    template="Summarize the following text:\n\n{text}\n\nSummary:"
)
chain = LLMChain(llm=llm, prompt=prompt)

# 注册为 capability
app.register_langchain_runnable(
    name="summarize",
    runnable=chain,
    description="Summarize text using LangChain",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to summarize"}
        },
        "required": ["text"]
    }
)

# 执行
result = await app.execute_capability(
    name="summarize",
    input={"text": "Long text to summarize..."}
)
print(result["summary"])
```

### 示例 2：使用装饰器注册

```python
from owlclaw import OwlClawApp
from langchain.chains import LLMChain

app = OwlClawApp()

@app.handler(
    name="qa",
    description="Answer questions using LangChain",
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "context": {"type": "string"}
        },
        "required": ["question", "context"]
    }
)
def qa_handler(input: dict) -> dict:
    # 创建 QA chain
    chain = create_qa_chain()
    
    # 执行
    answer = chain.invoke({
        "question": input["question"],
        "context": input["context"]
    })
    
    return {"answer": answer}
```

### 示例 3：配置 Fallback 和重试

```python
@app.handler(
    name="summarize",
    description="Summarize text with fallback",
    input_schema={...},
    fallback="summarize_simple",
    retry_policy={
        "max_attempts": 3,
        "initial_delay_ms": 100,
        "max_delay_ms": 5000,
        "backoff_multiplier": 2.0,
        "retryable_errors": ["TimeoutError", "RateLimitError"]
    }
)
def summarize_handler(input: dict) -> dict:
    # 主处理逻辑（可能失败）
    chain = create_complex_chain()
    return chain.invoke(input)

@app.handler(name="summarize_simple")
def summarize_simple_handler(input: dict) -> dict:
    # 简单的降级逻辑
    text = input["text"]
    return {"summary": text[:100] + "..."}
```

### 示例 4：自定义输入输出转换

```python
def custom_input_transformer(input: dict) -> dict:
    """自定义输入转换"""
    return {
        "text": input["content"],
        "max_length": input.get("max_length", 100)
    }

def custom_output_transformer(output: str) -> dict:
    """自定义输出转换"""
    return {
        "summary": output,
        "length": len(output),
        "timestamp": datetime.now().isoformat()
    }

app.register_langchain_runnable(
    name="summarize",
    runnable=chain,
    description="Summarize with custom transformers",
    input_schema={...},
    input_transformer=custom_input_transformer,
    output_transformer=custom_output_transformer
)
```

## 部署考虑

### 依赖管理

**requirements.txt**：
```
owlclaw[langchain]>=1.0.0
langchain>=0.1.0,<0.3.0
langchain-core>=0.1.0,<0.3.0
```

**pyproject.toml**：
```toml
[project.optional-dependencies]
langchain = [
    "langchain>=0.1.0,<0.3.0",
    "langchain-core>=0.1.0,<0.3.0",
]
```

### 性能优化

1. **连接池**：复用 LLM 客户端连接
2. **并发控制**：限制最大并发执行数
3. **超时控制**：设置合理的超时时间
4. **缓存**：缓存常用的 Runnable 实例

### 监控指标

- 执行次数（按 capability 分组）
- 执行成功率
- 执行延迟（P50/P95/P99）
- 错误率（按错误类型分组）
- Fallback 使用率
- 重试次数

### 告警规则

- 执行成功率 < 95%
- P95 延迟 > 5秒
- 错误率 > 5%
- Fallback 使用率 > 20%

## 参考文档

- **LangChain 文档**：https://python.langchain.com/docs/
- **LangChain Runnable 接口**：https://python.langchain.com/docs/expression_language/interface
- **OwlClaw 架构分析**：docs/ARCHITECTURE_ANALYSIS.md
- **Capabilities 系统设计**：.kiro/specs/capabilities/design.md
- **Governance 系统设计**：.kiro/specs/governance/design.md
- **Langfuse 集成设计**：.kiro/specs/integrations-langfuse/design.md

---

**维护者**：平台研发  
**最后更新**：2025-01-15
```

### 端到端测试

**测试场景**：
1. 完整的 Runnable 注册和执行流程
2. 与 Governance Layer 的集成
3. 与 Ledger 的集成
4. 与 Langfuse 的集成
5. Fallback 机制
6. 重试机制

**示例测试**：
```python
@pytest.mark.asyncio
async def test_end_to_end_langchain_execution():
    """端到端测试：从注册到执行"""
    # 创建 mock 组件
    app = create_test_app()
    governance = MockGovernanceLayer()
    ledger = MockLedger()
    
    # 创建 LangChain Runnable
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain.llms import FakeListLLM
    
    prompt = PromptTemplate(
        input_variables=["text"],
        template="Summarize: {text}"
    )
    llm = FakeListLLM(responses=["This is a summary"])
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # 注册 Runnable
    adapter = LangChainAdapter(app, config)
    adapter.register_runnable(
        runnable=chain,
        config=RunnableConfig(
            name="summarize",
            description="Summarize text",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            }
        )
    )
    
    # 执行
    result = await app.execute_capability(
        name="summarize",
        input={"text": "Long text to summarize..."},
        context=create_test_context()
    )
    
    # 验证结果
    assert result["status"] == "success"
    assert "summary" in result or "result" in result
    
    # 验证 Governance Layer 被调用
    assert governance.validate_called
    
    # 验证 Ledger 记录
    records = ledger.get_records()
    assert len(records) == 1
    assert records[0]["capability_name"] == "summarize"
    assert records[0]["status"] == "success"
```

### 性能测试

**测试目标**：
- 验证适配层开销 < 20ms (P95)
- 验证支持每秒 100+ 次执行
- 验证支持 10+ 个并发执行

**测试工具**：
- locust：负载测试
- pytest-benchmark：性能基准测试

**示例测试**：
```python
import pytest
from locust import HttpUser, task, between

def test_adapter_overhead(benchmark):
    """测试适配层开销"""
    adapter = LangChainAdapter(app, config)
    runnable = create_simple_runnable()
    
    def execute():
        return adapter.execute(
            runnable,
            {"text": "test"},
            create_test_context(),
            create_test_config()
        )
    
    result = benchmark(execute)
    
    # 验证开销 < 20ms
    assert result.stats.mean < 0.02  # 20ms

class LangChainLoadTest(HttpUser):
    """负载测试"""
    wait_time = between(0.1, 0.5)
    
    @task
    def execute_runnable(self):
        self.client.post("/capabilities/summarize", json={
            "text": "Test text to summarize"
        })

# 运行负载测试
# locust -f test_performance.py --host=http://localhost:8000
```

## 部署考虑

### 1. 依赖管理

#### 可选依赖配置

```python
# setup.py

setup(
    name="owlclaw",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "httpx>=0.24.0",
        # 核心依赖...
    ],
    extras_require={
        "langchain": [
            "langchain>=0.1.0,<0.3.0",
            "langchain-core>=0.1.0,<0.3.0",
            "jsonschema>=4.0.0",
        ],
        "all": [
            "langchain>=0.1.0,<0.3.0",
            "langchain-core>=0.1.0,<0.3.0",
            "jsonschema>=4.0.0",
            # 其他可选依赖...
        ],
    },
)
```

#### 版本检查

```python
def check_langchain_version():
    """检查 LangChain 版本兼容性"""
    try:
        import langchain
        from packaging import version
        
        current_version = version.parse(langchain.__version__)
        min_version = version.parse("0.1.0")
        max_version = version.parse("0.3.0")
        
        if not (min_version <= current_version < max_version):
            raise ImportError(
                f"LangChain version {langchain.__version__} is not supported. "
                f"Please install version >= {min_version} and < {max_version}"
            )
    except ImportError:
        raise ImportError(
            "LangChain is not installed. "
            "Install it with: pip install owlclaw[langchain]"
        )
```

### 2. 配置管理

#### 配置文件示例

```yaml
# config/langchain.yaml

langchain:
  enabled: true
  
  # 版本验证
  version_check: true
  min_version: "0.1.0"
  max_version: "0.3.0"
  
  # 执行配置
  default_timeout_seconds: 30
  max_concurrent_executions: 10
  
  # 可观测性
  tracing:
    enabled: true
    langfuse_integration: true
  
  # 隐私保护
  privacy:
    mask_inputs: false
    mask_outputs: false
    mask_patterns:
      - "api_key"
      - "password"
      - "token"
      - "secret"
```

#### 环境变量

```bash
# .env

# LangChain 配置
OWLCLAW_LANGCHAIN_ENABLED=true
OWLCLAW_LANGCHAIN_TIMEOUT=30
OWLCLAW_LANGCHAIN_TRACING_ENABLED=true

# Langfuse 配置
LANGFUSE_PUBLIC_KEY=pk_xxx
LANGFUSE_SECRET_KEY=sk_xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. 监控和告警

#### Prometheus 指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
langchain_executions_total = Counter(
    'langchain_executions_total',
    'Total number of LangChain executions',
    ['capability', 'status']
)

langchain_execution_duration = Histogram(
    'langchain_execution_duration_seconds',
    'Time spent executing LangChain Runnables',
    ['capability']
)

langchain_active_executions = Gauge(
    'langchain_active_executions',
    'Number of active LangChain executions',
    ['capability']
)

langchain_fallback_used = Counter(
    'langchain_fallback_used_total',
    'Total number of times fallback was used',
    ['capability', 'reason']
)

# 在代码中使用
langchain_executions_total.labels(
    capability=config.name,
    status='success'
).inc()

langchain_execution_duration.labels(
    capability=config.name
).observe(duration)
```

#### 告警规则

```yaml
# prometheus-alerts.yaml

groups:
- name: langchain_integration
  rules:
  - alert: LangChainHighFailureRate
    expr: rate(langchain_executions_total{status="failed"}[5m]) / rate(langchain_executions_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "LangChain execution failure rate is high"
      description: "{{ $value | humanizePercentage }} of executions are failing"

  - alert: LangChainHighLatency
    expr: histogram_quantile(0.95, rate(langchain_execution_duration_seconds_bucket[5m])) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "LangChain execution latency is high"
      description: "P95 latency is {{ $value }}s"

  - alert: LangChainFrequentFallback
    expr: rate(langchain_fallback_used_total[5m]) > 0.5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "LangChain fallback is frequently used"
      description: "Fallback is being used {{ $value }} times per second"
```

### 4. 安全考虑

#### 输入验证

```python
def validate_input_safety(input_data: Dict[str, Any]) -> None:
    """验证输入数据的安全性"""
    # 检查输入大小
    import json
    input_size = len(json.dumps(input_data))
    if input_size > 1024 * 1024:  # 1MB
        raise ValueError(f"Input size {input_size} exceeds limit")
    
    # 检查嵌套深度
    def check_depth(obj, current_depth=0, max_depth=10):
        if current_depth > max_depth:
            raise ValueError(f"Input nesting depth exceeds {max_depth}")
        if isinstance(obj, dict):
            for value in obj.values():
                check_depth(value, current_depth + 1, max_depth)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, current_depth + 1, max_depth)
    
    check_depth(input_data)
```

#### 输出脱敏

```python
import re

def mask_sensitive_data(data: Any, patterns: List[str]) -> Any:
    """脱敏敏感数据"""
    if isinstance(data, str):
        for pattern in patterns:
            # 使用正则表达式匹配并替换
            data = re.sub(
                pattern,
                lambda m: m.group(0)[:3] + '*' * (len(m.group(0)) - 3),
                data,
                flags=re.IGNORECASE
            )
        return data
    elif isinstance(data, dict):
        return {k: mask_sensitive_data(v, patterns) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_sensitive_data(item, patterns) for item in data]
    else:
        return data

# 使用
masked_output = mask_sensitive_data(
    output,
    patterns=[
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
        r'\b\d{3}-\d{4}-\d{4}\b',  # 电话号码
        r'\b(api[_-]?key|token|secret|password)\s*[:=]\s*\S+\b',  # API keys
    ]
)
```

### 5. 故障排查

#### 日志配置

```python
import logging

# 配置 LangChain 集成日志
logger = logging.getLogger('owlclaw.integrations.langchain')
logger.setLevel(logging.INFO)

# 添加处理器
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)

# 在代码中使用
logger.info(f"Executing LangChain Runnable: {config.name}")
logger.debug(f"Input: {input}")
logger.debug(f"Output: {output}")
logger.error(f"Execution failed: {error}", exc_info=True)
```

#### 调试模式

```python
class LangChainAdapter:
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.debug = config.debug if hasattr(config, 'debug') else False
    
    async def execute(self, runnable, input, context, config):
        if self.debug:
            # 记录详细的调试信息
            logger.debug(f"=== LangChain Execution Debug ===")
            logger.debug(f"Runnable: {type(runnable).__name__}")
            logger.debug(f"Config: {config}")
            logger.debug(f"Input: {json.dumps(input, indent=2)}")
        
        # 执行...
        
        if self.debug:
            logger.debug(f"Output: {json.dumps(output, indent=2)}")
            logger.debug(f"Duration: {duration}ms")
            logger.debug(f"=== End Debug ===")
```

#### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| ImportError: No module named 'langchain' | LangChain 未安装 | `pip install owlclaw[langchain]` |
| ValidationError: Input validation failed | 输入不符合 schema | 检查 input_schema 定义和输入数据 |
| TimeoutError: Execution timeout | Runnable 执行时间过长 | 增加 timeout_seconds 或优化 Runnable |
| RateLimitError: Rate limit exceeded | 超过 LLM API 速率限制 | 配置重试策略或降低并发 |
| TypeError: Expected Runnable | 注册的对象不是 Runnable | 确保对象实现 Runnable 接口 |

## 迁移指南

### 从纯 LangChain 迁移到 OwlClaw

#### 步骤 1：安装 OwlClaw

```bash
pip install owlclaw[langchain]
```

#### 步骤 2：创建 OwlClaw 应用

```python
from owlclaw import OwlClawApp

app = OwlClawApp(
    name="my-agent",
    config_path="config/owlclaw.yaml"
)
```

#### 步骤 3：注册现有 LangChain Chain

```python
# 原有代码
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

prompt = PromptTemplate(
    input_variables=["text"],
    template="Summarize the following text: {text}"
)
llm = OpenAI(temperature=0.7)
chain = LLMChain(llm=llm, prompt=prompt)

# 迁移后：注册为 capability
@app.handler(
    name="summarize",
    description="Summarize text using LangChain",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        },
        "required": ["text"]
    }
)
def summarize_handler(input: dict) -> dict:
    result = chain.run(input["text"])
    return {"summary": result}
```

#### 步骤 4：调用 Capability

```python
# 原有调用方式
result = chain.run("Long text to summarize...")

# 迁移后：通过 OwlClaw 调用
result = await app.execute_capability(
    name="summarize",
    input={"text": "Long text to summarize..."}
)
summary = result["summary"]
```

#### 步骤 5：添加治理和审计

```python
# 配置治理策略
app.governance.add_policy(
    name="rate_limit_summarize",
    capability="summarize",
    rate_limit={"max_calls": 100, "window_seconds": 60}
)

# 查询审计日志
records = await app.ledger.query(
    capability_name="summarize",
    start_time=datetime.now() - timedelta(days=1)
)
```

### 最佳实践

1. **Schema 定义**：
   - 使用详细的 JSON Schema 定义输入
   - 包含 description 字段帮助理解
   - 使用 required 字段标记必需参数

2. **错误处理**：
   - 为关键 capability 配置 fallback
   - 配置合理的重试策略
   - 记录详细的错误日志

3. **性能优化**：
   - 使用异步 Runnable（ainvoke）
   - 配置合理的超时时间
   - 限制并发执行数量

4. **安全性**：
   - 启用输入输出脱敏
   - 配置权限控制策略
   - 定期审查审计日志

5. **可观测性**：
   - 启用 Langfuse 集成
   - 配置 Prometheus 指标
   - 设置告警规则

## 总结

LangChain 集成为 OwlClaw 提供了强大的编排能力，使得：

1. **无缝集成**：现有 LangChain 代码可以直接注册为 capability
2. **治理一致**：LangChain 执行受相同的治理和审计约束
3. **可观测性**：完整的追踪和监控支持
4. **易于迁移**：提供清晰的迁移路径和最佳实践
5. **可选依赖**：不影响核心 SDK 的体积和复杂度

通过隔离设计、完善的错误处理、配置管理和监控告警，该集成在提供强大功能的同时，保持了系统的稳定性和可维护性。

---

**维护者**：平台研发  
**最后更新**：2026-02-22
