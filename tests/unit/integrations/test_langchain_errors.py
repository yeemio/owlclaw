"""Tests for ErrorHandler with property checks."""

from __future__ import annotations

import asyncio

from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.errors import ErrorHandler


class RateLimitError(Exception):
    """Test-only rate limit exception type."""


def test_create_error_response_shape() -> None:
    response = ErrorHandler.create_error_response(
        error_type="ValidationError",
        message="invalid input",
        status_code=400,
    )

    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["message"] == "invalid input"
    assert response["error"]["status_code"] == 400


@given(st.sampled_from([ValueError("bad"), TimeoutError("slow"), Exception("unknown")]))
def test_map_exception_always_returns_structured_payload(error: Exception) -> None:
    handler = ErrorHandler()
    payload = handler.map_exception(error)

    assert "error" in payload
    assert "type" in payload["error"]
    assert "message" in payload["error"]
    assert "status_code" in payload["error"]


def test_map_exception_uses_specific_mapping_for_known_exception_types() -> None:
    handler = ErrorHandler()
    handler.EXCEPTION_MAPPING["RateLimitError"] = ("RateLimitError", 429)

    payload = handler.map_exception(RateLimitError("limit"))

    assert payload["error"]["type"] == "RateLimitError"
    assert payload["error"]["status_code"] == 429


def test_handle_fallback_invokes_executor() -> None:
    async def fallback_executor(name: str, input_data: dict, context: object, error: Exception) -> dict:
        return {"name": name, "input": input_data, "context": str(context), "error": str(error)}

    handler = ErrorHandler(fallback_executor=fallback_executor)

    result = asyncio.run(
        handler.handle_fallback(
            "fallback_handler",
            {"text": "hello"},
            context="ctx",
            error=RuntimeError("boom"),
        )
    )

    assert result["name"] == "fallback_handler"
    assert result["_fallback_used"] is True
