from __future__ import annotations

from types import SimpleNamespace

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.integrations.queue_adapters.kafka import KafkaQueueAdapter


def _record(
    *,
    value: bytes,
    topic: str,
    partition: int,
    offset: int,
    key: bytes | None,
    headers: list[tuple[str, bytes]],
) -> SimpleNamespace:
    return SimpleNamespace(
        topic=topic,
        partition=partition,
        offset=offset,
        key=key,
        value=value,
        headers=headers,
        timestamp=1_700_000_000_000,
    )


@given(
    topic=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=20),
    partition=st.integers(min_value=0, max_value=8),
    offset=st.integers(min_value=0, max_value=10_000),
    payload=st.binary(max_size=256),
    key_text=st.one_of(st.none(), st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)),
    headers_map=st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=12),
        values=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", max_size=20),
        max_size=5,
    ),
)
@settings(max_examples=30, deadline=None)
def test_property_kafka_adapter_interface_consistency(
    topic: str,
    partition: int,
    offset: int,
    payload: bytes,
    key_text: str | None,
    headers_map: dict[str, str],
) -> None:
    """Feature: triggers-queue, Property 1: 适配器接口一致性."""
    adapter = KafkaQueueAdapter(
        topic=topic,
        bootstrap_servers="localhost:9092",
        consumer_group="g1",
        consumer=object(),
        producer=object(),
    )

    raw_headers = [(k, v.encode("utf-8")) for k, v in headers_map.items()]
    if "x-message-id" in headers_map:
        raw_headers = [("x-message-id", headers_map["x-message-id"].encode("utf-8"))] + [
            (k, v.encode("utf-8")) for k, v in headers_map.items() if k != "x-message-id"
        ]

    record = _record(
        value=payload,
        topic=topic,
        partition=partition,
        offset=offset,
        key=(None if key_text is None else key_text.encode("utf-8")),
        headers=raw_headers,
    )

    message = adapter._record_to_raw_message(record)

    expected_message_id = headers_map.get("x-message-id") or key_text or f"{topic}:{partition}:{offset}"
    assert message.message_id == expected_message_id
    assert message.body == payload
    assert message.metadata["topic"] == topic
    assert message.metadata["partition"] == partition
    assert message.metadata["offset"] == offset
    for header_key, header_value in headers_map.items():
        assert message.headers.get(header_key) == header_value
