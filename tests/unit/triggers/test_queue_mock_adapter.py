from __future__ import annotations

from datetime import datetime, timezone

import pytest

from owlclaw.integrations.queue_adapters import MockQueueAdapter
from owlclaw.triggers.queue import RawMessage


@pytest.mark.asyncio
async def test_mock_queue_adapter_ack_nack_dlq_flow() -> None:
    adapter = MockQueueAdapter()
    await adapter.connect()

    msg = RawMessage(
        message_id="m-1",
        body=b"hello",
        headers={},
        timestamp=datetime.now(timezone.utc),
        metadata={},
    )
    adapter.enqueue(msg)

    consumed = [item async for item in adapter.consume()]
    assert len(consumed) == 1
    assert consumed[0].message_id == "m-1"

    await adapter.ack(consumed[0])
    await adapter.nack(consumed[0], requeue=True)
    await adapter.send_to_dlq(consumed[0], reason="parse failed")

    assert adapter.get_acked() == ["m-1"]
    assert adapter.get_nacked() == [("m-1", True)]
    assert adapter.get_dlq() == [("m-1", "parse failed")]

    await adapter.close()
    assert await adapter.health_check() is False
