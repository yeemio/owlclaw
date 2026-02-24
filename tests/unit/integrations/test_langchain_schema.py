"""Tests for SchemaBridge with property checks."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.integrations.langchain.schema import SchemaBridge, SchemaValidationError

SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
    },
    "required": ["text"],
}


@given(st.text(min_size=1))
def test_validate_input_accepts_valid_payload(text: str) -> None:
    SchemaBridge.validate_input({"text": text}, SCHEMA)


@given(st.one_of(st.integers(), st.none(), st.lists(st.integers())))
def test_validate_input_rejects_invalid_payload_types(invalid_value: Any) -> None:
    with pytest.raises(SchemaValidationError):
        SchemaBridge.validate_input({"text": invalid_value}, SCHEMA)


@given(st.dictionaries(keys=st.text(min_size=1), values=st.integers()))
def test_transform_output_preserves_dict_output(payload: dict[str, int]) -> None:
    assert SchemaBridge.transform_output(payload) == payload


@given(st.one_of(st.integers(), st.text(), st.none(), st.lists(st.integers())))
def test_transform_output_wraps_non_dict_output(payload: Any) -> None:
    result = SchemaBridge.transform_output(payload)
    assert result == {"result": payload}


def test_transform_input_uses_custom_transformer() -> None:
    transformed = SchemaBridge.transform_input({"text": "hello"}, lambda data: data["text"].upper())
    assert transformed == "HELLO"
