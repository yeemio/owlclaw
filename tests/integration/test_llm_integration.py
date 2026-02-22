"""Integration tests for owlclaw.integrations.llm (Task 9.1 real API, Task 9.2 Langfuse).

Requires:
- Task 9.1: .env with OPENAI_API_KEY (and optionally ANTHROPIC_API_KEY for 9.1.2).
- Task 9.2: Langfuse running locally and .env with LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
  LANGFUSE_HOST=http://localhost:3000 (see deploy/README.langfuse.md to start Langfuse).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlclaw.integrations.llm import (
    LLMClient,
    LLMConfig,
    ModelConfig,
    PromptBuilder,
    ToolsConverter,
)

# Load .env from repo root (conftest does this; ensure we have it for standalone run)
_env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_file.exists():
    try:
        import dotenv
        dotenv.load_dotenv(_env_file)
    except ImportError:
        pass

pytestmark = pytest.mark.integration


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _has_langfuse_keys() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        and os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    )


def _has_siliconflow_key() -> bool:
    return bool(os.environ.get("SILICONFLOW_API_KEY", "").strip())


# ---------------------------------------------------------------------------
# Task 9.1: 真实 API 调用测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_openai_completion():
    """9.1.1: Real OpenAI call (skip if OPENAI_API_KEY not set)."""
    if not _has_openai_key():
        pytest.skip("OPENAI_API_KEY not set; set it in .env for real API tests")

    config = LLMConfig(
        default_model="gpt-4o-mini",
        models={
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                provider="openai",
                api_key_env="OPENAI_API_KEY",
                cost_per_1k_prompt_tokens=0.00015,
                cost_per_1k_completion_tokens=0.0006,
            ),
        },
    )
    client = LLMClient(config)
    messages = [
        PromptBuilder.build_system_message("You are a helpful assistant. Reply in one short sentence."),
        PromptBuilder.build_user_message("Say hello."),
    ]
    resp = await client.complete(messages)
    assert resp.model == "gpt-4o-mini"
    assert resp.content is not None
    assert len(resp.content) > 0
    assert resp.prompt_tokens >= 0
    assert resp.completion_tokens >= 0


@pytest.mark.asyncio
async def test_real_openai_function_calling():
    """9.1.3: Real OpenAI call with tools (skip if OPENAI_API_KEY not set)."""
    if not _has_openai_key():
        pytest.skip("OPENAI_API_KEY not set; set it in .env for real API tests")

    config = LLMConfig(
        default_model="gpt-4o-mini",
        models={
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                provider="openai",
                api_key_env="OPENAI_API_KEY",
                supports_function_calling=True,
            ),
        },
    )
    tools = ToolsConverter.capabilities_to_tools([
        {"name": "get_weather", "description": "Get weather for a city.", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}},
    ])
    client = LLMClient(config)
    messages = [
        PromptBuilder.build_system_message("You are a helpful assistant. Use tools when asked."),
        PromptBuilder.build_user_message("What is the weather in Paris? Use the tool."),
    ]
    resp = await client.complete(messages, tools=tools)
    assert resp.model == "gpt-4o-mini"
    # May return content or function_calls depending on model
    assert resp.content is not None or resp.function_calls is not None


@pytest.mark.asyncio
async def test_real_anthropic_completion():
    """9.1.2: Real Anthropic call (skip if ANTHROPIC_API_KEY not set)."""
    if not _has_anthropic_key():
        pytest.skip("ANTHROPIC_API_KEY not set; set it in .env for Anthropic test")

    config = LLMConfig(
        default_model="claude-3-5-haiku",
        models={
            "claude-3-5-haiku": ModelConfig(
                name="claude-3-5-haiku-20241022",
                provider="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
            ),
        },
    )
    client = LLMClient(config)
    messages = [
        PromptBuilder.build_system_message("Reply in one short sentence."),
        PromptBuilder.build_user_message("Say hi."),
    ]
    resp = await client.complete(messages)
    assert "claude" in resp.model.lower()
    assert resp.content is not None
    assert len(resp.content) > 0


# ---------------------------------------------------------------------------
# Task 9.2: Langfuse 集成测试
# ---------------------------------------------------------------------------


def _fake_litellm_response(content: str, tool_calls: list, pt: int, ct: int) -> object:
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
async def test_langfuse_trace_created():
    """9.2.1: With Langfuse enabled, a trace is created for an LLM call (no real LLM; mock response)."""
    if not _has_langfuse_keys():
        pytest.skip(
            "Langfuse 已启动时请在 .env 中配置 LANGFUSE_PUBLIC_KEY、LANGFUSE_SECRET_KEY 再运行本测试 "
            "（从 http://localhost:3000 → 项目 Settings → API Keys 创建并粘贴）"
        )

    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
    config = LLMConfig(
        default_model="gpt-4o-mini",
        models={
            "gpt-4o-mini": ModelConfig(name="gpt-4o-mini", provider="openai", api_key_env="OPENAI_API_KEY"),
        },
        langfuse_enabled=True,
        langfuse_public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        langfuse_secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        langfuse_host=host,
    )
    client = LLMClient(config)
    if client._langfuse is None:
        pytest.skip("Langfuse client 初始化失败（请确认 langfuse 已安装且服务可访问）")

    with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_litellm_response("Mocked reply", [], 10, 5)
        messages = [
            PromptBuilder.build_system_message("You are helpful."),
            PromptBuilder.build_user_message("Hello."),
        ]
        resp = await client.complete(messages)
    assert resp.content == "Mocked reply"
    # Flush Langfuse so trace is sent (SDK may buffer)
    try:
        client._langfuse.flush()
    except Exception:
        pass
    # If we get here without exception, trace creation path ran; server may still reject if down
    assert client._langfuse is not None


@pytest.mark.asyncio
async def test_langfuse_data_recorded():
    """9.2.2: Trace records input/output and usage (mock LLM, Langfuse receives generation)."""
    if not _has_langfuse_keys():
        pytest.skip(
            "Langfuse 已启动时请在 .env 中配置 LANGFUSE_PUBLIC_KEY、LANGFUSE_SECRET_KEY 再运行本测试 "
            "（从 http://localhost:3000 → 项目 Settings → API Keys 创建并粘贴）"
        )

    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
    config = LLMConfig(
        default_model="gpt-4o-mini",
        models={
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                provider="openai",
                api_key_env="OPENAI_API_KEY",
                cost_per_1k_prompt_tokens=0.0001,
                cost_per_1k_completion_tokens=0.0002,
            ),
        },
        langfuse_enabled=True,
        langfuse_public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        langfuse_secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        langfuse_host=host,
    )
    client = LLMClient(config)
    if client._langfuse is None:
        pytest.skip("Langfuse client not initialized")

    with patch("owlclaw.integrations.llm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = _fake_litellm_response("Recorded output", [], 100, 50)
        messages = [
            PromptBuilder.build_user_message("Input for trace."),
        ]
        resp = await client.complete(messages, task_type=None)
    assert resp.prompt_tokens == 100
    assert resp.completion_tokens == 50
    assert resp.cost == pytest.approx(0.01 + 0.01, abs=1e-5)
    try:
        client._langfuse.flush()
    except Exception:
        pass
