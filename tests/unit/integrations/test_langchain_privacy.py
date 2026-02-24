"""Tests for PrivacyMasker and adapter masking integration."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.adapter import LangChainAdapter, RunnableConfig
from owlclaw.integrations.langchain.config import LangChainConfig
from owlclaw.integrations.langchain.privacy import PrivacyMasker


class DummyRunnable:
    async def ainvoke(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"echo": data["text"]}


class AppWithLedger:
    def __init__(self) -> None:
        self.registry = type("Registry", (), {"register_handler": lambda self, name, handler: None})()
        self.records: list[dict[str, Any]] = []

    async def record_langchain_execution(self, payload: dict[str, Any]) -> None:
        self.records.append(payload)


def _cfg() -> RunnableConfig:
    return RunnableConfig(
        name="privacy",
        description="privacy",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


@given(st.from_regex(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}", fullmatch=True))
def test_pii_email_is_masked(email: str) -> None:
    masker = PrivacyMasker()
    masked = masker.mask_data(email)
    assert "@" in masked
    assert email != masked


def test_mask_phone_number() -> None:
    masker = PrivacyMasker()
    masked = masker.mask_data("Call me at 138-1234-5678")
    assert "***-****-****" in masked


def test_mask_api_key_like_text() -> None:
    masker = PrivacyMasker()
    masked = masker.mask_data("api_key: sk-test-secret-token")
    assert "api_key" in masked
    assert "sk-test-secret-token" not in masked


def test_mask_custom_pattern() -> None:
    masker = PrivacyMasker(custom_patterns=[r"customer_id=\d+"])
    masked = masker.mask_data("customer_id=12345")
    assert masked == "***"


@pytest.mark.asyncio
async def test_adapter_masks_input_output_in_ledger_records() -> None:
    app = AppWithLedger()
    config = LangChainConfig()
    config.privacy.mask_inputs = True
    config.privacy.mask_outputs = True
    adapter = LangChainAdapter(app, config)

    await adapter.execute(DummyRunnable(), {"text": "api_key: sk-live-123456"}, None, _cfg())

    record = app.records[-1]
    assert "sk-live-123456" not in str(record["input"])
    assert "sk-live-123456" not in str(record["output"])
