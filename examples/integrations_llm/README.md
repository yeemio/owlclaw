# LLM 集成示例

本目录演示 `owlclaw.integrations.llm` 的用法：配置加载、基本调用、function calling、模型路由。示例均支持 **mock 模式**（无需 API Key 即可运行）。

## 运行方式

```bash
# 从项目根目录执行
poetry run python examples/integrations_llm/basic_call.py
poetry run python examples/integrations_llm/function_calling.py
poetry run python examples/integrations_llm/model_routing.py
```

## 配置

- 真实调用：将 `owlclaw.yaml` 放在当前工作目录或通过环境变量指定，并设置 `OPENAI_API_KEY` 等。
- Mock 模式：示例中使用的配置已开启 `mock_mode`，不会发起真实请求。
- 配置示例见 `docs/llm/owlclaw.llm.example.yaml`。
