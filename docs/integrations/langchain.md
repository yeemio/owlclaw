# LangChain 集成指南

## 快速开始（<5 分钟）

1. 安装可选依赖：

```bash
pip install "owlclaw[langchain]"
```

2. 在业务应用中挂载 Skills 并注册 runnable：

```python
from owlclaw import OwlClaw

app = OwlClaw("my-agent")
app.mount_skills("./capabilities")

class EchoRunnable:
    async def ainvoke(self, payload: dict) -> dict:
        return {"echo": payload["text"]}

app.register_langchain_runnable(
    name="entry-monitor",
    runnable=EchoRunnable(),
    description="Echo runnable",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
```

3. 通过 `registry.invoke_handler` 或 Agent Runtime 调用 capability。

## 配置说明

可在 `owlclaw.yaml` 或 `app.configure(langchain={...})` 设置：

- `enabled`
- `version_check`
- `min_version` / `max_version`
- `default_timeout_seconds`
- `max_concurrent_executions`
- `tracing.enabled`
- `tracing.langfuse_integration`
- `privacy.mask_inputs`
- `privacy.mask_outputs`
- `privacy.mask_patterns`

示例见 `config/langchain.example.yaml`。

## 错误处理

内置映射：

- `ValueError` / `SchemaValidationError` -> `ValidationError` (400)
- `TimeoutError` -> `TimeoutError` (504)
- `RateLimitError` -> `RateLimitError` (429)
- 其他异常 -> `InternalError` (500)

支持 fallback 和指数退避重试。

## 最佳实践

- 优先使用 `ainvoke`，同步 runnable 仅作兼容。
- 为关键 capability 配置 `fallback` + `retry_policy`。
- 开启 `privacy.mask_inputs/mask_outputs` 后再落审计。
- 用 `execute_stream` 处理长响应和进度输出。

## 故障排查

- `ImportError: langchain is not installed`：安装 `owlclaw[langchain]`。
- `version not supported`：调整 LangChain 版本到 `>=0.1.0,<0.3.0`。
- `PolicyDeniedError`：检查治理层 `validate_capability_execution` 返回值。
- `FallbackError`：检查 fallback capability 是否已注册。
