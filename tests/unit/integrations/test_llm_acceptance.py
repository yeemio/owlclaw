"""Acceptance tests for owlclaw.integrations.llm (integrations-llm Task 12).

Task 12.1: Functional acceptance (requirements, error handling, config).
Task 12.2: Performance acceptance (latency, concurrency).
Task 12.3: Cost acceptance (cost formula, tracking).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

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
)


def _fake_litellm_response(content: str, tool_calls: list, pt: int, ct: int) -> object:
    """Minimal litellm-like response with usage."""
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


# ---------------------------------------------------------------------------
# Task 12.1: Functional acceptance
# ---------------------------------------------------------------------------


class TestAcceptanceFunctional:
    """12.1: Verify all requirements, error handling, config management."""

    def test_acceptance_config_loads_from_example_yaml(self) -> None:
        """12.1.3: Config management - example YAML loads and validates."""
        example = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "llm" / "owlclaw.llm.example.yaml"
        if not example.exists():
            pytest.skip("docs/llm/owlclaw.llm.example.yaml not found")
        config = LLMConfig.from_yaml(example)
        assert config.default_model
        assert len(config.models) >= 1
        assert any("gpt-4o" in m for m in config.models)

    def test_acceptance_default_config_and_routing(self) -> None:
        """12.1.1: Requirements - default config and task_type routing."""
        config = LLMConfig.default_for_owlclaw()
        client = LLMClient(config)
        model_name, model_config, fallback = client._route_model(None)
        assert model_name == "gpt-4o-mini"
        assert model_config.provider == "openai"
        assert fallback == []

        config2 = LLMConfig(
            default_model="gpt-4o-mini",
            models={
                "gpt-4o": ModelConfig(name="gpt-4o", provider="openai"),
                "gpt-4o-mini": ModelConfig(name="gpt-4o-mini", provider="openai"),
            },
            task_type_routing=[
                TaskTypeRouting(task_type="trading", model="gpt-4o", fallback_models=["gpt-4o-mini"]),
            ],
        )
        client2 = LLMClient(config2)
        name, _, fb = client2._route_model("trading")
        assert name == "gpt-4o"
        assert fb == ["gpt-4o-mini"]

    def test_acceptance_tools_conversion(self) -> None:
        """12.1.1: Requirements - capabilities to tools schema."""
        caps = [
            {
                "name": "get_weather",
                "description": "Get weather for a city.",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
        ]
        tools = ToolsConverter.capabilities_to_tools(caps)
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "get_weather"
        assert "parameters" in tools[0]["function"]

    def test_acceptance_prompt_builder_and_estimator(self) -> None:
        """12.1.1: Requirements - system/user messages and token estimation."""
        sys_msg = PromptBuilder.build_system_message("You are a bot.")
        user_msg = PromptBuilder.build_user_message("Hello.")
        assert sys_msg["role"] == "system"
        assert user_msg["role"] == "user"
        est = TokenEstimator("gpt-4o-mini")
        n = est.estimate_messages_tokens([sys_msg, user_msg])
        assert n >= 1

    @pytest.mark.asyncio
    async def test_acceptance_complete_mock_returns_valid_response(self) -> None:
        """12.1.1: Requirements - complete() returns content, model, tokens."""
        config = LLMConfig.default_for_owlclaw()
        config.mock_mode = True
        config.mock_responses = {"default": "Acceptance reply"}
        client = LLMClient(config)
        messages = [
            PromptBuilder.build_system_message("Assistant."),
            PromptBuilder.build_user_message("Hi"),
        ]
        resp = await client.complete(messages)
        assert resp.content == "Acceptance reply"
        assert resp.model == "mock"
        assert resp.prompt_tokens >= 1
        assert resp.completion_tokens >= 1
        assert resp.total_tokens == resp.prompt_tokens + resp.completion_tokens

    @pytest.mark.asyncio
    async def test_acceptance_error_handling_auth(self) -> None:
        """12.1.2: Error handling - AuthenticationError raised."""
        config = LLMConfig.default_for_owlclaw()
        client = LLMClient(config)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("AuthenticationError: Invalid API key")
            with pytest.raises(AuthenticationError):
                await client.complete(messages=[{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_acceptance_error_handling_rate_limit(self) -> None:
        """12.1.2: Error handling - RateLimitError raised."""
        config = LLMConfig.default_for_owlclaw()
        config.max_retries = 0
        client = LLMClient(config)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("RateLimitError: Too many requests")
            with pytest.raises(RateLimitError):
                await client.complete(messages=[{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_acceptance_error_handling_context_window(self) -> None:
        """12.1.2: Error handling - ContextWindowExceededError raised."""
        config = LLMConfig(
            default_model="tiny",
            models={
                "tiny": ModelConfig(
                    name="tiny",
                    provider="openai",
                    context_window=10,
                ),
            },
        )
        client = LLMClient(config)
        long_messages = [{"role": "user", "content": "x" * 100}]
        with pytest.raises(ContextWindowExceededError):
            await client.complete(long_messages)

    @pytest.mark.asyncio
    async def test_acceptance_error_handling_service_unavailable(self) -> None:
        """12.1.2: Error handling - ServiceUnavailableError raised."""
        config = LLMConfig.default_for_owlclaw()
        config.max_retries = 0
        client = LLMClient(config)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("ServiceUnavailable: 503")
            with pytest.raises(ServiceUnavailableError):
                await client.complete(messages=[{"role": "user", "content": "Hi"}])


# ---------------------------------------------------------------------------
# Task 12.2: Performance acceptance
# ---------------------------------------------------------------------------


class TestAcceptancePerformance:
    """12.2: Latency and concurrency (mock-based)."""

    @pytest.mark.asyncio
    async def test_acceptance_single_call_latency(self) -> None:
        """12.2.1: Single complete() returns within acceptable time (mock)."""
        config = LLMConfig.default_for_owlclaw()
        config.mock_mode = True
        config.mock_responses = {"default": "Fast"}
        client = LLMClient(config)
        start = time.perf_counter()
        await client.complete([{"role": "user", "content": "Hi"}])
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, "Mock complete() should finish within 5s"

    @pytest.mark.asyncio
    async def test_acceptance_concurrent_calls(self) -> None:
        """12.2.2: Multiple concurrent complete() calls all succeed (mock)."""
        config = LLMConfig.default_for_owlclaw()
        config.mock_mode = True
        config.mock_responses = {"default": "OK"}
        client = LLMClient(config)
        messages = [{"role": "user", "content": "Hi"}]
        tasks = [client.complete(messages) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        for r in results:
            assert r.content == "OK"
            assert r.model == "mock"


# ---------------------------------------------------------------------------
# Task 12.3: Cost acceptance
# ---------------------------------------------------------------------------


class TestAcceptanceCost:
    """12.3: Cost calculation and tracking."""

    @pytest.mark.asyncio
    async def test_acceptance_cost_calculation_accuracy(self) -> None:
        """12.3.1: Cost = (prompt_tokens/1000)*cost_p + (completion_tokens/1000)*cost_c."""
        config = LLMConfig(
            default_model="gpt-4o-mini",
            models={
                "gpt-4o-mini": ModelConfig(
                    name="gpt-4o-mini",
                    provider="openai",
                    api_key_env="OPENAI_API_KEY",
                    cost_per_1k_prompt_tokens=0.001,
                    cost_per_1k_completion_tokens=0.002,
                ),
            },
        )
        client = LLMClient(config)
        with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _fake_litellm_response("ok", [], 1000, 500)
            resp = await client.complete([{"role": "user", "content": "Hi"}])
        expected = 1000 / 1000 * 0.001 + 500 / 1000 * 0.002
        assert abs(resp.cost - expected) < 1e-6
        assert resp.prompt_tokens == 1000
        assert resp.completion_tokens == 500

    @pytest.mark.asyncio
    async def test_acceptance_cost_tracking_on_response(self) -> None:
        """12.3.2: Every response exposes cost and total_tokens for tracking."""
        config = LLMConfig.default_for_owlclaw()
        config.mock_mode = True
        config.mock_responses = {"default": "Tracked"}
        client = LLMClient(config)
        resp = await client.complete([{"role": "user", "content": "Hi"}])
        assert hasattr(resp, "cost")
        assert hasattr(resp, "total_tokens")
        assert resp.total_tokens == resp.prompt_tokens + resp.completion_tokens
        assert isinstance(resp.cost, int | float)
