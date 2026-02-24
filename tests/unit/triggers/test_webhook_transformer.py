from __future__ import annotations

import pytest

from owlclaw.triggers.webhook import (
    FieldMapping,
    HttpRequest,
    PayloadTransformer,
    TransformationRule,
)


def test_transformer_parses_complex_nested_json() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(
        headers={"Content-Type": "application/json"},
        body='{"order":{"id":"o-1","items":[{"sku":"a"},{"sku":"b"}]},"price":"12.5"}',
    )
    parsed = transformer.parse(request)
    rule = TransformationRule(
        id="r1",
        name="order",
        target_agent_id="agent-orders",
        mappings=[
            FieldMapping(source="$.order.id", target="order_id"),
            FieldMapping(source="$.price", target="price", transform="number"),
        ],
        target_schema={
            "required": ["order_id", "price"],
            "properties": {"order_id": {"type": "string"}, "price": {"type": "number"}},
        },
    )

    transformed = transformer.transform(parsed, rule)
    assert transformed.agent_id == "agent-orders"
    assert transformed.parameters["order_id"] == "o-1"
    assert transformed.parameters["price"] == 12.5


def test_transformer_parses_xml_with_namespace() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(
        headers={"Content-Type": "application/xml"},
        body='<n:root xmlns:n="urn:test"><n:user><n:id>u-1</n:id></n:user></n:root>',
    )

    parsed = transformer.parse(request)
    assert parsed.data["root"]["user"]["id"] == "u-1"


def test_transformer_parses_form_with_special_characters() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="title=hello%20world&currency=%E2%82%AC&note=%E6%B5%8B%E8%AF%95",
    )

    parsed = transformer.parse(request)
    assert parsed.data["title"] == "hello world"
    assert parsed.data["currency"] == "€"
    assert parsed.data["note"] == "测试"


def test_transformer_custom_logic_and_schema_validation() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(headers={"Content-Type": "application/json"}, body='{"amount":"8.5"}')
    parsed = transformer.parse(request)
    rule = TransformationRule(
        id="r2",
        name="logic",
        target_agent_id="agent-logic",
        mappings=[FieldMapping(source="$.amount", target="amount", transform="number")],
        custom_logic='{"double_amount": parameters["amount"] * 2}',
        target_schema={
            "required": ["amount", "double_amount"],
            "properties": {"amount": {"type": "number"}, "double_amount": {"type": "number"}},
        },
    )

    transformed = transformer.transform(parsed, rule)
    assert transformed.parameters["amount"] == 8.5
    assert transformed.parameters["double_amount"] == 17.0


def test_transformer_parse_safe_returns_400_for_invalid_payload() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(headers={"Content-Type": "application/json"}, body='{"bad_json": }')
    parsed, result = transformer.parse_safe(request)

    assert parsed is None
    assert not result.valid
    assert result.error is not None
    assert result.error.code == "INVALID_FORMAT"
    assert result.error.status_code == 400


def test_transformer_rejects_invalid_custom_logic_expression() -> None:
    transformer = PayloadTransformer()
    request = HttpRequest(headers={"Content-Type": "application/json"}, body='{"x":"1"}')
    parsed = transformer.parse(request)
    rule = TransformationRule(
        id="r3",
        name="unsafe",
        target_agent_id="agent-unsafe",
        mappings=[FieldMapping(source="$.x", target="x")],
        custom_logic='{"x": __import__("os").system("echo bad")}',
    )

    with pytest.raises(ValueError, match="unsafe custom logic expression"):
        transformer.transform(parsed, rule)
