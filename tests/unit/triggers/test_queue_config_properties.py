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
    default_tenant_id=_SAFE_TEXT,
    trust_tenant_header=st.booleans(),
    tenant_header_name=_SAFE_TEXT,
    trusted_producer_header=_SAFE_TEXT,
    trusted_producers=st.lists(_SAFE_TEXT, min_size=0, max_size=4),
    tenant_signature_header=_SAFE_TEXT,
    tenant_signature_secret_env=st.one_of(st.none(), _SAFE_TEXT),
    tenant_signature_secret_envs=st.one_of(st.none(), st.lists(_SAFE_TEXT, min_size=0, max_size=4)),
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
    default_tenant_id: str,
    trust_tenant_header: bool,
    tenant_header_name: str,
    trusted_producer_header: str,
    trusted_producers: list[str],
    tenant_signature_header: str,
    tenant_signature_secret_env: str | None,
    tenant_signature_secret_envs: list[str] | None,
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
                f"  default_tenant_id: '{default_tenant_id}'\n"
                f"  trust_tenant_header: {str(trust_tenant_header).lower()}\n"
                f"  tenant_header_name: '{tenant_header_name}'\n"
                f"  trusted_producer_header: '{trusted_producer_header}'\n"
                f"  trusted_producers: [{', '.join(repr(item) for item in trusted_producers)}]\n"
                f"  tenant_signature_header: '{tenant_signature_header}'\n"
                + (
                    ""
                    if tenant_signature_secret_env is None
                    else f"  tenant_signature_secret_env: '{tenant_signature_secret_env}'\n"
                )
                + (
                    ""
                    if tenant_signature_secret_envs is None
                    else f"  tenant_signature_secret_envs: [{', '.join(repr(item) for item in tenant_signature_secret_envs)}]\n"
                )
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
        assert config.default_tenant_id == default_tenant_id
        assert config.trust_tenant_header == trust_tenant_header
        assert config.tenant_header_name == tenant_header_name
        assert config.trusted_producer_header == trusted_producer_header
        assert config.trusted_producers == trusted_producers
        assert config.tenant_signature_header == tenant_signature_header
        assert config.tenant_signature_secret_env == tenant_signature_secret_env
        assert config.tenant_signature_secret_envs == tenant_signature_secret_envs
