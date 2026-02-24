from __future__ import annotations

import pytest

from owlclaw.triggers.queue import BinaryParser, JSONParser, ParseError, TextParser


def test_json_parser_parses_object() -> None:
    parser = JSONParser()
    payload = parser.parse(b'{"event":"created","count":1}')
    assert payload["event"] == "created"
    assert payload["count"] == 1


def test_json_parser_rejects_non_object() -> None:
    parser = JSONParser()
    with pytest.raises(ParseError):
        parser.parse(b"[1,2,3]")


def test_text_parser_invalid_utf8_raises_parse_error() -> None:
    parser = TextParser()
    with pytest.raises(ParseError):
        parser.parse(b"\xff\xfe")


def test_binary_parser_returns_raw_bytes() -> None:
    parser = BinaryParser()
    data = b"\x00\x01\x02"
    assert parser.parse(data) == data
