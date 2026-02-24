from __future__ import annotations

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import WebhookConfigManager, WebhookGlobalConfig, WebhookSystemConfig


@given(
    timeout=st.floats(min_value=1, max_value=120, allow_nan=False, allow_infinity=False),
    retries=st.integers(min_value=0, max_value=10),
    log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
@settings(max_examples=25, deadline=None)
def test_property_configuration_loading_and_application(timeout: float, retries: int, log_level: str) -> None:
    """Feature: triggers-webhook, Property 31: 配置加载和应用."""

    manager = WebhookConfigManager()
    loaded = manager.load_from_mapping(
        {"global": {"timeout_seconds": timeout, "max_retries": retries, "log_level": log_level}, "endpoints": {}}
    )
    os.environ["OWLCLAW_WEBHOOK_TIMEOUT_SECONDS"] = str(timeout + 1)
    try:
        applied = manager.apply_env_overrides(loaded)
    finally:
        os.environ.pop("OWLCLAW_WEBHOOK_TIMEOUT_SECONDS", None)
    assert applied.global_config.timeout_seconds == timeout + 1


@given(
    endpoint_a_timeout=st.floats(min_value=1, max_value=30, allow_nan=False, allow_infinity=False),
    endpoint_b_timeout=st.floats(min_value=31, max_value=60, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=25, deadline=None)
def test_property_endpoint_independent_configuration(endpoint_a_timeout: float, endpoint_b_timeout: float) -> None:
    """Feature: triggers-webhook, Property 32: 端点独立配置."""

    manager = WebhookConfigManager()
    cfg = WebhookSystemConfig(
        global_config=WebhookGlobalConfig(),
        endpoints={
            "ep-a": {"timeout_seconds": endpoint_a_timeout},
            "ep-b": {"timeout_seconds": endpoint_b_timeout},
        },
    )
    manager.update(cfg)
    current = manager.get_current()
    assert current.endpoints["ep-a"]["timeout_seconds"] != current.endpoints["ep-b"]["timeout_seconds"]


@given(
    timeout_before=st.floats(min_value=1, max_value=20, allow_nan=False, allow_infinity=False),
    timeout_after=st.floats(min_value=21, max_value=60, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=25, deadline=None)
def test_property_configuration_rollback_roundtrip(timeout_before: float, timeout_after: float) -> None:
    """Feature: triggers-webhook, Property 33: 配置版本回滚往返."""

    manager = WebhookConfigManager()
    before = WebhookSystemConfig(global_config=WebhookGlobalConfig(timeout_seconds=timeout_before))
    after = WebhookSystemConfig(global_config=WebhookGlobalConfig(timeout_seconds=timeout_after))
    v1 = manager.update(before)
    manager.update(after)
    restored = manager.rollback(v1)
    assert restored.global_config.timeout_seconds == timeout_before
