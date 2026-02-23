"""Unit tests for security config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from owlclaw.config.manager import ConfigManager
from owlclaw.config.models import OwlClawConfig


def test_security_config_loads_from_yaml(tmp_path: Path) -> None:
    ConfigManager._reset_for_tests()
    cfg_path = tmp_path / "owlclaw.yaml"
    cfg_path.write_text(
        """
security:
  sanitizer:
    enabled: false
  risk_gate:
    enabled: true
    confirmation_timeout_seconds: 120
  data_masker:
    enabled: true
""",
        encoding="utf-8",
    )
    cfg = ConfigManager.load(config_path=str(cfg_path)).get()
    assert cfg.security.sanitizer.enabled is False
    assert cfg.security.risk_gate.confirmation_timeout_seconds == 120
    assert cfg.security.data_masker.enabled is True


def test_security_config_validation_rejects_invalid_timeout() -> None:
    with pytest.raises(ValidationError):
        OwlClawConfig.model_validate(
            {
                "security": {
                    "risk_gate": {
                        "enabled": True,
                        "confirmation_timeout_seconds": 0,
                    }
                }
            }
        )

