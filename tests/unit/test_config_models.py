"""Unit tests for OwlClaw configuration models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlclaw.config.models import OwlClawConfig


def test_owlclaw_config_defaults() -> None:
    cfg = OwlClawConfig()
    assert cfg.agent.heartbeat_interval_minutes == 30
    assert cfg.integrations.llm.model == "gpt-4o-mini"
    assert cfg.triggers.cron.max_concurrent == 10
    assert cfg.triggers.governance.max_daily_runs == 24
    assert cfg.triggers.retry.max_retries == 3
    assert cfg.triggers.notifications.enabled is False
    assert cfg.security.risk_gate.confirmation_timeout_seconds == 300


def test_owlclaw_config_nested_validation_error() -> None:
    with pytest.raises(ValidationError):
        OwlClawConfig.model_validate(
            {"agent": {"heartbeat_interval_minutes": 0}}
        )


def test_owlclaw_config_validates_cron_nested_fields() -> None:
    with pytest.raises(ValidationError):
        OwlClawConfig.model_validate({"triggers": {"retry": {"max_retries": -1}}})

