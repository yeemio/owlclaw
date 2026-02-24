from __future__ import annotations

import json
from datetime import datetime, timezone

from hypothesis import given
from hypothesis import strategies as st

from owlclaw.triggers.queue import BinaryParser, JSONParser, MessageEnvelope, RawMessage, TextParser


@given(
    content=st.text(alphabet=st.characters(blacklist_categories=["Cs"])),
    headers=st.dictionaries(st.text(min_size=1), st.text(), max_size=5),
)
def test_property_queue_message_parsing_multi_format(content: str, headers: dict[str, str]) -> None:
    """Feature: triggers-queue, Property 3: 多格式消息解析."""
    encoded = content.encode("utf-8")
    json_payload = JSONParser().parse(json.dumps({"value": content}).encode("utf-8"))
    text_payload = TextParser().parse(encoded)
    binary_payload = BinaryParser().parse(encoded)

    assert isinstance(json_payload, dict)
    assert text_payload == content
    assert binary_payload == encoded
    assert isinstance(headers, dict)


@given(
    message_id=st.text(min_size=1),
    body=st.binary(max_size=1024),
    source=st.text(min_size=1, max_size=40),
)
def test_property_message_envelope_completeness(message_id: str, body: bytes, source: str) -> None:
    """Feature: triggers-queue, Property 2: 消息封装完整性."""
    raw = RawMessage(
        message_id=message_id,
        body=body,
        headers={},
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )

    envelope = MessageEnvelope.from_raw_message(raw, source=source, parser=BinaryParser())

    assert envelope.message_id == message_id
    assert envelope.payload == body
    assert envelope.source == source
    assert envelope.headers == {}
    assert envelope.received_at is not None
