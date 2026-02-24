from __future__ import annotations

import asyncio
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import (
    FieldMapping,
    HttpRequest,
    PayloadTransformer,
    TransformationRule,
)


@given(
    value=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=24),
)
@settings(max_examples=40, deadline=None)
def test_property_payload_parsing_correctness(value: str) -> None:
    """Feature: triggers-webhook, Property 8: 负载解析正确性."""

    async def _run() -> None:
        transformer = PayloadTransformer()
        payload = {"payload": {"value": value}}
        request = HttpRequest(headers={"Content-Type": "application/json"}, body=json.dumps(payload))
        parsed = transformer.parse(request)
        assert parsed.data == payload

    asyncio.run(_run())


@given(
    numeric=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=40, deadline=None)
def test_property_transformation_rule_application_correctness(numeric: float) -> None:
    """Feature: triggers-webhook, Property 9: 转换规则应用正确性."""

    async def _run() -> None:
        transformer = PayloadTransformer()
        request = HttpRequest(headers={"Content-Type": "application/json"}, body=json.dumps({"amount": str(numeric)}))
        parsed = transformer.parse(request)
        rule = TransformationRule(
            id="prop-rule",
            name="prop",
            target_agent_id="agent-prop",
            mappings=[FieldMapping(source="$.amount", target="amount", transform="number")],
            target_schema={"required": ["amount"], "properties": {"amount": {"type": "number"}}},
        )
        transformed = transformer.transform(parsed, rule)
        assert transformed.parameters["amount"] == float(str(numeric))

    asyncio.run(_run())


@given(invalid_payload=st.text(min_size=1, max_size=40))
@settings(max_examples=30, deadline=None)
def test_property_payload_parsing_failure_returns_400(invalid_payload: str) -> None:
    """Feature: triggers-webhook, Property 10: 负载解析失败返回 400."""

    async def _run() -> None:
        transformer = PayloadTransformer()
        request = HttpRequest(headers={"Content-Type": "application/json"}, body=invalid_payload)
        _, result = transformer.parse_safe(request)
        # Valid JSON strings like "\"x\"" are parsed as scalar and should be rejected as non-object.
        assert not result.valid
        assert result.error is not None
        assert result.error.status_code == 400

    asyncio.run(_run())
