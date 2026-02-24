"""Tests for LangChainConfig."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlclaw.integrations.langchain.config import LangChainConfig


def test_config_from_yaml_loads_langchain_section(tmp_path: Path) -> None:
    config_path = tmp_path / "owlclaw.yaml"
    config_path.write_text(
        """
langchain:
  enabled: true
  version_check: true
  min_version: "0.1.0"
  max_version: "0.3.0"
  default_timeout_seconds: 25
  max_concurrent_executions: 4
  tracing:
    enabled: true
    langfuse_integration: false
  privacy:
    mask_inputs: true
    mask_outputs: false
    mask_patterns: ["password"]
""".strip(),
        encoding="utf-8",
    )

    config = LangChainConfig.from_yaml(config_path)

    assert config.enabled is True
    assert config.default_timeout_seconds == 25
    assert config.max_concurrent_executions == 4
    assert config.tracing.langfuse_integration is False
    assert config.privacy.mask_inputs is True
    assert config.privacy.mask_patterns == ["password"]


def test_config_from_yaml_replaces_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_TIMEOUT", "45")
    monkeypatch.setenv("MASK_KEY", "api_key")

    config_path = tmp_path / "owlclaw.yaml"
    config_path.write_text(
        """
langchain:
  default_timeout_seconds: ${LC_TIMEOUT}
  privacy:
    mask_patterns:
      - ${MASK_KEY}
""".strip(),
        encoding="utf-8",
    )

    config = LangChainConfig.from_yaml(config_path)

    assert config.default_timeout_seconds == 45
    assert config.privacy.mask_patterns == ["api_key"]


def test_config_validate_rejects_invalid_semver_order() -> None:
    config = LangChainConfig(min_version="0.3.0", max_version="0.1.0")
    with pytest.raises(ValueError, match="min_version"):
        config.validate_semantics()


def test_config_from_yaml_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        LangChainConfig.from_yaml("not-found.yaml")
