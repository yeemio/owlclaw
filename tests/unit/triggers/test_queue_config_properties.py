from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.queue import load_queue_trigger_config

_SAFE_TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-", min_size=1, max_size=20)


@given(
    queue_name=_SAFE_TEXT,
    consumer_group=_SAFE_TEXT,
    concurrency=st.integers(min_value=1, max_value=32),
    ack_policy=st.sampled_from(["ack", "nack", "requeue", "dlq"]),
    max_retries=st.integers(min_value=0, max_value=10),
    retry_backoff_base=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    retry_backoff_multiplier=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    idempotency_window=st.integers(min_value=1, max_value=86400),
    enable_dedup=st.booleans(),
    parser_type=st.sampled_from(["json", "text", "binary"]),
)
@settings(max_examples=30, deadline=None)
def test_property_queue_config_application(
    queue_name: str,
    consumer_group: str,
    concurrency: int,
    ack_policy: str,
    max_retries: int,
    retry_backoff_base: float,
    retry_backoff_multiplier: float,
    idempotency_window: int,
    enable_dedup: bool,
    parser_type: str,
) -> None:
    """Feature: triggers-queue, Property 5: 配置正确应用."""
    with TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "queue.yaml"
        config_file.write_text(
            (
                "queue_trigger:\n"
                f"  queue_name: '{queue_name}'\n"
                f"  consumer_group: '{consumer_group}'\n"
                f"  concurrency: {concurrency}\n"
                f"  ack_policy: {ack_policy}\n"
                f"  max_retries: {max_retries}\n"
                f"  retry_backoff_base: {retry_backoff_base}\n"
                f"  retry_backoff_multiplier: {retry_backoff_multiplier}\n"
                f"  idempotency_window: {idempotency_window}\n"
                f"  enable_dedup: {str(enable_dedup).lower()}\n"
                f"  parser_type: {parser_type}\n"
                "  event_name_header: x-event-name\n"
            ),
            encoding="utf-8",
        )

        config = load_queue_trigger_config(str(config_file))

        assert config.queue_name == queue_name
        assert config.consumer_group == consumer_group
        assert config.concurrency == concurrency
        assert config.ack_policy == ack_policy
        assert config.max_retries == max_retries
        assert config.retry_backoff_base == retry_backoff_base
        assert config.retry_backoff_multiplier == retry_backoff_multiplier
        assert config.idempotency_window == idempotency_window
        assert config.enable_dedup == enable_dedup
        assert config.parser_type == parser_type
