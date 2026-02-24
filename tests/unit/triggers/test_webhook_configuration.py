from __future__ import annotations

import pytest

from owlclaw.triggers.webhook import WebhookConfigManager, WebhookGlobalConfig, WebhookSystemConfig


def test_configuration_rejects_invalid_values() -> None:
    manager = WebhookConfigManager()
    invalid = WebhookSystemConfig(global_config=WebhookGlobalConfig(timeout_seconds=0, max_retries=1, log_level="INFO"))
    with pytest.raises(ValueError, match="timeout_seconds"):
        manager.validate(invalid)


def test_configuration_hot_update_notifies_listener() -> None:
    manager = WebhookConfigManager()
    observed: list[WebhookSystemConfig] = []
    manager.watch(lambda cfg: observed.append(cfg))
    config = WebhookSystemConfig(
        global_config=WebhookGlobalConfig(timeout_seconds=45, max_retries=2, log_level="DEBUG"),
        endpoints={"ep-1": {"timeout_seconds": 5}},
    )
    version = manager.update(config)

    assert version == "v1"
    assert len(observed) == 1
    assert observed[0].global_config.timeout_seconds == 45


def test_configuration_rollback_restores_previous_version() -> None:
    manager = WebhookConfigManager()
    base = WebhookSystemConfig(global_config=WebhookGlobalConfig(timeout_seconds=30, max_retries=3, log_level="INFO"))
    updated = WebhookSystemConfig(global_config=WebhookGlobalConfig(timeout_seconds=10, max_retries=1, log_level="ERROR"))
    v1 = manager.update(base)
    manager.update(updated)

    restored = manager.rollback(v1)
    assert restored.global_config.timeout_seconds == 30
    assert restored.global_config.max_retries == 3
