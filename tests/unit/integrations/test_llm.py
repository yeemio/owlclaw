"""Unit tests for owlclaw.integrations.llm (integrations-llm Task 8)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from owlclaw.integrations.langfuse import TraceContext
from owlclaw.integrations.llm import (
    AuthenticationError,
    ContextWindowExceededError,
    LLMClient,
    LLMConfig,
    ModelConfig,
    PromptBuilder,
    RateLimitError,
    ServiceUnavailableError,
    TaskTypeRouting,
    TokenEstimator,
    ToolsConverter,
    acompletion,
)


class TestLLMConfig:
    def test_default_for_owlclaw(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        assert c.default_model == "gpt-4o-mini"
        assert "gpt-4o-mini" in c.models
        assert c.models["gpt-4o-mini"].provider == "openai"

    def test_from_yaml(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "owlclaw.yaml"
        yaml_path.write_text("""
llm:
  default_model: gpt-4o
  models:
    gpt-4o:
      name: gpt-4o
      provider: openai
      api_key_env: OPENAI_API_KEY
      temperature: 0.7
      max_tokens: 4096
  task_type_routing:
    - task_type: trading
      model: gpt-4o
      fallback_models: [gpt-4o-mini]
""")
        c = LLMConfig.from_yaml(yaml_path)
        assert c.default_model == "gpt-4o"
        assert "gpt-4o" in c.models
        assert len(c.task_type_routing) == 1
        assert c.task_type_routing[0].task_type == "trading"
        assert c.task_type_routing[0].fallback_models == ["gpt-4o-mini"]

    def test_from_yaml_missing_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            LLMConfig.from_yaml("/nonexistent/owlclaw.yaml")

    def test_from_yaml_substitutes_env_in_lists(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("MODEL_A", "gpt-4o")
        monkeypatch.setenv("MODEL_B", "gpt-4o-mini")
        yaml_path = tmp_path / "owlclaw.yaml"
        yaml_path.write_text("""
llm:
  default_model: ${MODEL_A}
  models:
    ${MODEL_A}:
      name: ${MODEL_A}
      provider: openai
      api_key_env: OPENAI_API_KEY
  task_type_routing:
    - task_type: trading
      model: ${MODEL_A}
      fallback_models: ["${MODEL_B}"]
""")
        c = LLMConfig.from_yaml(yaml_path)
        assert c.default_model == "gpt-4o"
        assert c.task_type_routing[0].model == "gpt-4o"
        assert c.task_type_routing[0].fallback_models == ["gpt-4o-mini"]

    def test_from_yaml_invalid_config_raises_validation_error(self, tmp_path: Path) -> None:
        """Invalid config structure or types raise Pydantic ValidationError (Task 8.1.3)."""
        yaml_path = tmp_path / "owlclaw.yaml"
        yaml_path.write_text("""
llm:
  default_model: gpt-4o
  models:
    gpt-4o:
      name: gpt-4o
      provider: openai
      temperature: "not_a_number"
""")
        with pytest.raises(ValidationError):
            LLMConfig.from_yaml(yaml_path)


class TestLLMClient:
    def test_route_model_default(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        client = LLMClient(c)
        name, mc, fallback = client._route_model(None)
        assert name == "gpt-4o-mini"
        assert fallback == []

    def test_route_model_task_type(self) -> None:
        c = LLMConfig(
            default_model="gpt-4o-mini",
            models={
                "gpt-4o": ModelConfig(name="gpt-4o", provider="openai"),
                "gpt-4o-mini": ModelConfig(name="gpt-4o-mini", provider="openai"),
            },
            task_type_routing=[
                TaskTypeRouting(task_type="trading", model="gpt-4o", fallback_models=["gpt-4o-mini"]),
            ],
        )
        client = LLMClient(c)
        name, mc, fallback = client._route_model("trading")
        assert name == "gpt-4o"
        assert fallback == ["gpt-4o-mini"]

    @pytest.mark.asyncio
    async def test_complete_mock_mode(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        c.mock_mode = True
        c.mock_responses = {"default": "Hello"}
        client = LLMClient(c)
        resp = await client.complete(
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert resp.content == "Hello"
        assert resp.model == "mock"
        # Simulated token usage (~4 chars per token, Task 7.1.3)
        assert resp.prompt_tokens >= 1
        assert resp.completion_tokens >= 1
        # "Hello" = 5 chars -> 5//4 = 1
        assert resp.completion_tokens == 1

    @pytest.mark.asyncio
    async def test_complete_mock_mode_function_calls(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        c.mock_mode = True
        c.mock_responses = {
            "default": {
                "function_calls": [
                    {
                        "name": "get_price",
                        "arguments": {"symbol": "AAPL"},
                    }
                ]
            }
        }
        client = LLMClient(c)
        resp = await client.complete(messages=[{"role": "user", "content": "check"}], tools=[{"type": "function"}])
        assert resp.content is None
        assert resp.model == "mock"
        assert len(resp.function_calls) == 1
        assert resp.function_calls[0]["name"] == "get_price"
        assert resp.function_calls[0]["arguments"] == {"symbol": "AAPL"}
        assert resp.function_calls[0]["id"] == "mock_call_1"
        assert resp.completion_tokens >= 1

    @pytest.mark.asyncio
    async def test_complete_mock_mode_function_calls_with_json_args_and_content(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        c.mock_mode = True
        c.mock_responses = {
            "default": {
                "content": "Need tool execution",
                "function_calls": [
                    {
                        "id": "call_1",
                        "name": "search_news",
                        "arguments": "{\"query\":\"AAPL\"}",
                    }
                ],
            }
        }
        client = LLMClient(c)
        resp = await client.complete(messages=[{"role": "user", "content": "news?"}])
        assert resp.content == "Need tool execution"
        assert len(resp.function_calls) == 1
        assert resp.function_calls[0]["id"] == "call_1"
        assert resp.function_calls[0]["name"] == "search_news"
        assert resp.function_calls[0]["arguments"] == {"query": "AAPL"}

    @pytest.mark.asyncio
    async def test_complete_delegates_to_acompletion(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _fake_litellm_response("ok", [], 10, 5)  # pt=10, ct=5
            resp = await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
            )
            mock.assert_awaited_once()
            assert resp.content == "ok"
            assert resp.prompt_tokens == 10
            assert resp.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_complete_wraps_auth_error(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("AuthenticationError: Invalid API key")
            with pytest.raises(AuthenticationError) as exc_info:
                await client.complete(messages=[{"role": "user", "content": "Hi"}])
            assert "Invalid API key" in str(exc_info.value)
            assert exc_info.value.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_complete_wraps_rate_limit_error(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        c.max_retries = 1
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("RateLimitError: Too many requests")
            with pytest.raises(RateLimitError) as exc_info:
                await client.complete(messages=[{"role": "user", "content": "Hi"}])
            assert "Too many" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_retries_same_model_on_rate_limit_then_succeeds(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        c.max_retries = 3
        c.retry_delay_seconds = 0
        client = LLMClient(c)
        with (
            patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock,
            patch("owlclaw.integrations.llm.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock.side_effect = [
                Exception("RateLimitError: Too many requests"),
                Exception("RateLimitError: Too many requests"),
                _fake_litellm_response("ok", [], 10, 5),
            ]
            resp = await client.complete(messages=[{"role": "user", "content": "Hi"}])
            assert resp.content == "ok"
            assert mock.await_count == 3
            assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_complete_exhausts_retries_then_uses_fallback(self) -> None:
        c = LLMConfig(
            default_model="primary",
            models={
                "primary": ModelConfig(name="primary", provider="openai"),
                "fallback": ModelConfig(name="fallback", provider="openai"),
            },
            task_type_routing=[
                TaskTypeRouting(task_type="trading", model="primary", fallback_models=["fallback"])
            ],
            max_retries=2,
            retry_delay_seconds=0,
        )
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                Exception("RateLimitError: Too many requests"),  # primary retry 1
                Exception("RateLimitError: Too many requests"),  # primary retry 2 -> fallback
                _fake_litellm_response("ok", [], 10, 5),         # fallback success
            ]
            resp = await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                task_type="trading",
            )
            assert resp.model == "fallback"
            assert mock.await_count == 3

    @pytest.mark.asyncio
    async def test_complete_stream_true_raises(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        client = LLMClient(c)
        with pytest.raises(ValueError, match="stream=True"):
            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )

    @pytest.mark.asyncio
    async def test_complete_raises_when_context_window_exceeded(self) -> None:
        c = LLMConfig(
            default_model="tiny-window-model",
            models={
                "tiny-window-model": ModelConfig(
                    name="tiny-window-model",
                    provider="openai",
                    context_window=50,
                ),
            },
        )
        client = LLMClient(c)
        long_content = "a" * 400  # 100 tokens by heuristic + message overhead
        messages = [{"role": "user", "content": long_content}]

        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            with pytest.raises(ContextWindowExceededError, match="exceed context window") as exc_info:
                await client.complete(messages=messages)
            assert exc_info.value.model == "tiny-window-model"
            mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_complete_uses_fallback_model_for_response_and_cost(self) -> None:
        c = LLMConfig(
            default_model="primary",
            models={
                "primary": ModelConfig(
                    name="primary",
                    provider="openai",
                    cost_per_1k_prompt_tokens=1.0,
                    cost_per_1k_completion_tokens=1.0,
                ),
                "fallback": ModelConfig(
                    name="fallback",
                    provider="openai",
                    cost_per_1k_prompt_tokens=0.1,
                    cost_per_1k_completion_tokens=0.2,
                ),
            },
            task_type_routing=[
                TaskTypeRouting(task_type="trading", model="primary", fallback_models=["fallback"])
            ],
            max_retries=1,
        )
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                Exception("ServiceUnavailableError: upstream down"),
                _fake_litellm_response("ok", [], 1000, 1000),
            ]
            resp = await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                task_type="trading",
            )

            assert resp.model == "fallback"
            assert resp.cost == 0.3

    @pytest.mark.asyncio
    async def test_complete_applies_task_routing_temperature_and_max_tokens(self) -> None:
        c = LLMConfig(
            default_model="gpt-4o-mini",
            models={
                "gpt-4o-mini": ModelConfig(
                    name="gpt-4o-mini",
                    provider="openai",
                    temperature=0.7,
                    max_tokens=4096,
                ),
            },
            task_type_routing=[
                TaskTypeRouting(
                    task_type="analysis",
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_tokens=256,
                )
            ],
        )
        client = LLMClient(c)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _fake_litellm_response("ok", [], 10, 5)
            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                task_type="analysis",
            )

            kwargs = mock.call_args.kwargs
            assert kwargs["temperature"] == 0.1
            assert kwargs["max_tokens"] == 256


class TestModelFallbackIntegration:
    """Integration tests for model fallback (Task 9.3)."""

    @pytest.mark.asyncio
    async def test_primary_model_failure_simulated_then_fallback_used(self) -> None:
        """9.3.1: Simulate primary model failure; 9.3.2: Verify fallback is executed."""
        config = LLMConfig(
            default_model="primary",
            models={
                "primary": ModelConfig(name="primary", provider="openai"),
                "fallback": ModelConfig(name="fallback", provider="openai"),
            },
            task_type_routing=[
                TaskTypeRouting(task_type="trading", model="primary", fallback_models=["fallback"])
            ],
            max_retries=1,
            retry_delay_seconds=0,
        )
        client = LLMClient(config)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                ServiceUnavailableError("Primary model down", model="primary"),
                _fake_litellm_response("Fallback reply", [], 5, 3),
            ]
            resp = await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                task_type="trading",
            )
        assert resp.model == "fallback"
        assert resp.content == "Fallback reply"
        assert mock.await_count == 2


class TestLLMErrors:
    """Tests for LLM error types (Task 6.1)."""

    def test_authentication_error(self) -> None:
        err = AuthenticationError("Invalid API key", model="gpt-4o")
        assert str(err) == "Invalid API key"
        assert err.model == "gpt-4o"
        assert isinstance(err, AuthenticationError)

    def test_rate_limit_error(self) -> None:
        err = RateLimitError("Rate limit exceeded", model="gpt-4o")
        assert "Rate limit" in str(err)
        assert err.model == "gpt-4o"

    def test_context_window_exceeded_error(self) -> None:
        err = ContextWindowExceededError("Token limit 128k exceeded")
        assert "128k" in str(err)
        assert err.model is None

    def test_service_unavailable_error(self) -> None:
        cause = ConnectionError("Connection refused")
        err = ServiceUnavailableError("Service down", model="claude", cause=cause)
        assert err.model == "claude"
        assert err.cause is cause
        assert err.cause.args[0] == "Connection refused"


class TestPromptBuilder:
    """Tests for PromptBuilder (Task 8.3.1)."""

    def test_build_system_message(self) -> None:
        msg = PromptBuilder.build_system_message("You are an assistant.")
        assert msg == {"role": "system", "content": "You are an assistant."}

    def test_build_user_message(self) -> None:
        msg = PromptBuilder.build_user_message("Hello!")
        assert msg == {"role": "user", "content": "Hello!"}

    def test_build_function_result_message_string(self) -> None:
        msg = PromptBuilder.build_function_result_message("call_1", "get_price", "42.0")
        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "call_1"
        assert msg["name"] == "get_price"
        assert msg["content"] == "42.0"

    def test_build_function_result_message_dict(self) -> None:
        result = {"price": 42.0, "symbol": "AAPL"}
        msg = PromptBuilder.build_function_result_message("call_2", "get_price", result)
        assert msg["role"] == "tool"
        import json
        parsed = json.loads(msg["content"])
        assert parsed["price"] == 42.0
        assert parsed["symbol"] == "AAPL"

    def test_build_function_result_message_none(self) -> None:
        msg = PromptBuilder.build_function_result_message("call_3", "do_action", None)
        assert msg["content"] == "null"


class TestToolsConverter:
    """Tests for ToolsConverter (Task 8.3.2)."""

    def test_capabilities_to_tools_basic(self) -> None:
        caps = [
            {
                "name": "get_price",
                "description": "Get stock price",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
            }
        ]
        tools = ToolsConverter.capabilities_to_tools(caps)
        assert len(tools) == 1
        t = tools[0]
        assert t["type"] == "function"
        assert t["function"]["name"] == "get_price"
        assert t["function"]["description"] == "Get stock price"
        assert t["function"]["parameters"]["properties"]["symbol"]["type"] == "string"

    def test_capabilities_to_tools_no_parameters(self) -> None:
        caps = [{"name": "ping", "description": "Ping"}]
        tools = ToolsConverter.capabilities_to_tools(caps)
        assert tools[0]["function"]["parameters"]["type"] == "object"
        assert tools[0]["function"]["parameters"]["properties"] == {}

    def test_capabilities_to_tools_empty(self) -> None:
        assert ToolsConverter.capabilities_to_tools([]) == []

    def test_normalise_schema_adds_defaults(self) -> None:
        schema = ToolsConverter._normalise_schema({})
        assert schema["type"] == "object"
        assert schema["properties"] == {}

    def test_normalise_schema_preserves_existing(self) -> None:
        schema = ToolsConverter._normalise_schema(
            {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
        )
        assert schema["required"] == ["x"]
        assert schema["properties"]["x"]["type"] == "integer"


class TestTokenEstimator:
    """Tests for TokenEstimator (Task 8.3.3)."""

    def test_estimate_tokens_empty(self) -> None:
        est = TokenEstimator()
        assert est.estimate_tokens("") == 0

    def test_estimate_tokens_nonempty(self) -> None:
        est = TokenEstimator()
        count = est.estimate_tokens("Hello, world!")
        assert count >= 1

    def test_estimate_tokens_fallback_heuristic(self) -> None:
        """Verify character-based fallback: 4 chars = 1 token."""
        est = TokenEstimator()
        est._tiktoken_available = False
        est._encoding = None
        assert est.estimate_tokens("abcd") == 1
        assert est.estimate_tokens("abcdefgh") == 2
        assert est.estimate_tokens("a") == 1  # max(1, 1//4) = 1

    def test_estimate_messages_tokens(self) -> None:
        est = TokenEstimator()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        total = est.estimate_messages_tokens(messages)
        assert total >= 2  # at least some tokens

    def test_check_context_window_fits(self) -> None:
        est = TokenEstimator()
        messages = [{"role": "user", "content": "Hi"}]
        assert est.check_context_window(messages, context_window=128000) is True

    def test_check_context_window_exceeds(self) -> None:
        est = TokenEstimator()
        est._tiktoken_available = False
        est._encoding = None
        long_content = "a" * 400  # 400 chars -> 100 tokens + overhead
        messages = [{"role": "user", "content": long_content}]
        assert est.check_context_window(messages, context_window=50) is False


def _fake_litellm_response(content: str, tool_calls: list, pt: int, ct: int) -> object:
    """Build a minimal litellm-like response."""
    class Usage:
        def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens

    class Message:
        pass

    msg = Message()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = type("Choice", (), {"message": msg})()
    resp = type("Response", (), {"choices": [choice], "usage": Usage(pt, ct)})()
    return resp


@pytest.mark.asyncio
async def test_acompletion_records_langfuse_generation_when_trace_context_present() -> None:
    recorded: list[dict[str, object]] = []

    class _Trace:
        def generation(self, **kwargs: object) -> None:
            recorded.append(kwargs)

    ctx = TraceContext(trace_id="trace-1", metadata={"langfuse_trace": _Trace()})
    TraceContext.set_current(ctx)
    try:
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _fake_litellm_response("ok", [], 10, 5)
            await acompletion(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}])
    finally:
        TraceContext.set_current(None)

    assert len(recorded) == 1
    assert recorded[0]["metadata"]["status"] == "success"
    assert recorded[0]["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_acompletion_records_error_generation_on_failure() -> None:
    recorded: list[dict[str, object]] = []

    class _Trace:
        def generation(self, **kwargs: object) -> None:
            recorded.append(kwargs)

    ctx = TraceContext(trace_id="trace-1", metadata={"langfuse_trace": _Trace()})
    TraceContext.set_current(ctx)
    try:
        with patch("litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("llm failed")
            with pytest.raises(RuntimeError, match="llm failed"):
                await acompletion(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}])
    finally:
        TraceContext.set_current(None)

    assert len(recorded) == 1
    assert recorded[0]["metadata"]["status"] == "error"
