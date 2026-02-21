# 设计文档

## 简介

本文档描述 OwlClaw 与 Langfuse 的集成设计。Langfuse 为 OwlClaw Agent 提供 LLM 调用追踪、成本分析和可观测性能力。集成采用隔离设计，所有 Langfuse 相关代码集中在 `owlclaw/integrations/langfuse.py` 中，便于未来替换或支持其他可观测性平台。

## 架构概览

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

**集成边界：**

**OwlClaw 自建部分：**
- Agent 运行时（身份、记忆、知识、决策）
- LLM 客户端（litellm 集成）
- 工具执行系统
- 治理层

**Langfuse 提供部分：**
- Trace 和 Span 管理
- Token 使用量统计
- 成本计算和聚合
- 延迟和成功率监控
- 人工标注和评分
- Dashboard UI

**隔离层职责：**
- 封装 Langfuse SDK 的复杂性
- 提供 OwlClaw 风格的 API
- 处理配置和连接管理
- 异步上报和批量处理
- 降级处理（Langfuse 不可用时）
- 隐私保护（脱敏）

## 组件设计

### 1. LangfuseClient

**职责：** 封装 Langfuse SDK，提供 OwlClaw 风格的 API。

#### 1.1 类定义

```python
from langfuse import Langfuse
from typing import Optional, Any
from pathlib import Path
import yaml
import re
from contextvars import ContextVar

# Context variable for trace propagation
_current_trace: ContextVar[Optional["TraceContext"]] = ContextVar("current_trace", default=None)

class LangfuseConfig:
    """Langfuse 连接配置"""
    
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
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "LangfuseConfig":
        """从 owlclaw.yaml 加载配置"""
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        langfuse_config = config.get("langfuse", {})
        return cls(**langfuse_config)


class TraceContext:
    """Trace 上下文，用于在 Agent Run 生命周期中传递"""
    
    def __init__(self, trace_id: str, langfuse_trace: Any):
        self.trace_id = trace_id
        self.langfuse_trace = langfuse_trace
        self.spans: dict[str, Any] = {}
    
    def add_span(self, span_name: str, span: Any):
        """添加 span 到上下文"""
        self.spans[span_name] = span
    
    def get_span(self, span_name: str) -> Optional[Any]:
        """获取 span"""
        return self.spans.get(span_name)


class LangfuseClient:
    """OwlClaw 对 Langfuse SDK 的封装客户端"""
    
    def __init__(self, config: LangfuseConfig):
        self.config = config
        self._client: Optional[Langfuse] = None
        self._is_connected = False
    
    def connect(self) -> None:
        """建立与 Langfuse Server 的连接"""
        if not self.config.enabled:
            print("Langfuse is disabled in config")
            return
        
        try:
            self._client = Langfuse(
                public_key=self.config.public_key,
                secret_key=self.config.secret_key,
                host=self.config.host,
                flush_at=self.config.batch_size,
                flush_interval=self.config.flush_interval_seconds,
            )
            self._is_connected = True
            print(f"Connected to Langfuse at {self.config.host}")
        except Exception as e:
            print(f"Failed to connect to Langfuse: {e}")
            print("Langfuse will be disabled for this session")
            self._is_connected = False
    
    def disconnect(self) -> None:
        """优雅关闭连接，flush 所有待上报的 trace"""
        if self._client and self._is_connected:
            try:
                self._client.flush()
                print("Flushed all pending traces to Langfuse")
            except Exception as e:
                print(f"Error flushing traces: {e}")
            finally:
                self._is_connected = False
    
    def create_trace(
        self,
        name: str,
        agent_id: str,
        run_id: str,
        trigger: str,
        focus: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[TraceContext]:
        """
        创建 Agent Run trace
        
        Args:
            name: Trace 名称
            agent_id: Agent ID
            run_id: Run ID
            trigger: 触发类型
            focus: Focus 内容
            metadata: 额外元数据
        
        Returns:
            TraceContext 或 None（如果 Langfuse 不可用）
        """
        if not self._is_connected:
            return None
        
        # 采样检查
        if not self._should_sample():
            return None
        
        try:
            trace_metadata = {
                "agent_id": agent_id,
                "run_id": run_id,
                "trigger": trigger,
            }
            
            if focus:
                trace_metadata["focus"] = focus
            
            if metadata:
                trace_metadata.update(metadata)
            
            langfuse_trace = self._client.trace(
                name=name,
                metadata=trace_metadata,
            )
            
            trace_ctx = TraceContext(
                trace_id=run_id,
                langfuse_trace=langfuse_trace,
            )
            
            # 设置到 context variable
            _current_trace.set(trace_ctx)
            
            return trace_ctx
        
        except Exception as e:
            print(f"Error creating trace: {e}")
            return None
```
