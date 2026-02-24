from __future__ import annotations

from pathlib import Path

import pytest

from owlclaw.triggers.queue import load_queue_trigger_config
from owlclaw.triggers.queue.config import _replace_env_vars


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_queue_trigger_config_reads_valid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(
        config_file,
        """
queue_trigger:
  queue_name: orders
  consumer_group: workers
  concurrency: 4
  ack_policy: requeue
  max_retries: 5
  retry_backoff_base: 0.5
  retry_backoff_multiplier: 3.0
  idempotency_window: 7200
  enable_dedup: false
  parser_type: text
  event_name_header: x-custom-event
  focus: ops
""".strip(),
    )

    config = load_queue_trigger_config(str(config_file))

    assert config.queue_name == "orders"
    assert config.consumer_group == "workers"
    assert config.concurrency == 4
    assert config.ack_policy == "requeue"
    assert config.max_retries == 5
    assert config.retry_backoff_base == pytest.approx(0.5)
    assert config.retry_backoff_multiplier == pytest.approx(3.0)
    assert config.idempotency_window == 7200
    assert config.enable_dedup is False
    assert config.parser_type == "text"
    assert config.event_name_header == "x-custom-event"
    assert config.focus == "ops"


def test_load_queue_trigger_config_applies_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(
        config_file,
        """
queue_trigger:
  queue_name: orders
  consumer_group: workers
""".strip(),
    )

    config = load_queue_trigger_config(str(config_file))

    assert config.concurrency == 1
    assert config.ack_policy == "ack"
    assert config.max_retries == 3
    assert config.retry_backoff_base == pytest.approx(1.0)
    assert config.retry_backoff_multiplier == pytest.approx(2.0)
    assert config.idempotency_window == 3600
    assert config.enable_dedup is True
    assert config.parser_type == "json"
    assert config.event_name_header == "x-event-name"
    assert config.focus is None


def test_load_queue_trigger_config_rejects_invalid_enums(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(
        config_file,
        """
queue_trigger:
  queue_name: orders
  consumer_group: workers
  ack_policy: bad
""".strip(),
    )

    with pytest.raises(ValueError, match="ack_policy"):
        load_queue_trigger_config(str(config_file))


def test_load_queue_trigger_config_rejects_invalid_numeric_type(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(
        config_file,
        """
queue_trigger:
  queue_name: orders
  consumer_group: workers
  concurrency: not-a-number
""".strip(),
    )

    with pytest.raises(ValueError, match="concurrency must be an integer"):
        load_queue_trigger_config(str(config_file))


def test_load_queue_trigger_config_replaces_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "queue.yaml"
    monkeypatch.setenv("QUEUE_NAME", "orders-env")
    monkeypatch.setenv("GROUP_NAME", "workers-env")
    _write_yaml(
        config_file,
        """
queue_trigger:
  queue_name: ${QUEUE_NAME}
  consumer_group: ${GROUP_NAME}
""".strip(),
    )

    config = load_queue_trigger_config(str(config_file))

    assert config.queue_name == "orders-env"
    assert config.consumer_group == "workers-env"


def test_replace_env_vars_recursively(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("A", "1")
    monkeypatch.setenv("B", "2")
    result = _replace_env_vars({"x": "${A}", "nested": [{"y": "v${B}"}]})

    assert result == {"x": "1", "nested": [{"y": "v2"}]}


def test_load_queue_trigger_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_queue_trigger_config(str(tmp_path / "missing.yaml"))


def test_load_queue_trigger_config_non_mapping_root_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(config_file, "- item")

    with pytest.raises(ValueError, match="root must be a mapping"):
        load_queue_trigger_config(str(config_file))


def test_load_queue_trigger_config_non_mapping_section_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "queue.yaml"
    _write_yaml(config_file, "queue_trigger: 123")

    with pytest.raises(ValueError, match="queue_trigger section must be a mapping"):
        load_queue_trigger_config(str(config_file))
