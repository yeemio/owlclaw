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
    LLMResponse,
    ModelConfig,
    RateLimitError,
    ServiceUnavailableError,
    TaskTypeRouting,
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
