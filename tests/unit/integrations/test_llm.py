"""Unit tests for owlclaw.integrations.llm (integrations-llm Task 8)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlclaw.integrations.llm import (
    AuthenticationError,
    ContextWindowExceededError,
    LLMClient,
    LLMConfig,
    ModelConfig,
    RateLimitError,
    ServiceUnavailableError,
    TaskTypeRouting,
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
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0

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
    async def test_complete_stream_true_raises(self) -> None:
        c = LLMConfig.default_for_owlclaw()
        client = LLMClient(c)
        with pytest.raises(ValueError, match="stream=True"):
            await client.complete(
                messages=[{"role": "user", "content": "Hi"}],
                stream=True,
            )

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
