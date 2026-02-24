from __future__ import annotations

import pytest

from owlclaw.capabilities.bindings import (
    HTTPBindingConfig,
    QueueBindingConfig,
    SQLBindingConfig,
    parse_binding_config,
    validate_binding_config,
)


def test_http_binding_parse_and_round_trip() -> None:
    payload = {
        "type": "http",
        "method": "POST",
        "url": "https://api.example.com/orders/{id}",
        "headers": {"Authorization": "${API_TOKEN}"},
        "body_template": {"order_id": "{id}"},
        "response_mapping": {"path": "$.data"},
        "timeout_ms": 3000,
        "retry": {"max_attempts": 2, "backoff_ms": 200, "backoff_multiplier": 1.5},
    }
    config = parse_binding_config(payload)
    assert isinstance(config, HTTPBindingConfig)
    assert config.method == "POST"
    assert config.url.endswith("/{id}")
    assert config.to_dict()["retry"]["max_attempts"] == 2


def test_queue_binding_parse_and_round_trip() -> None:
    payload = {
        "type": "queue",
        "provider": "kafka",
        "connection": "${KAFKA_DSN}",
        "topic": "orders.created",
        "format": "json",
        "headers_mapping": {"correlation_id": "{trace_id}"},
    }
    config = parse_binding_config(payload)
    assert isinstance(config, QueueBindingConfig)
    assert config.provider == "kafka"
    assert config.connection == "${KAFKA_DSN}"


def test_sql_binding_parse_and_round_trip() -> None:
    payload = {
        "type": "sql",
        "connection": "${READ_DB_DSN}",
        "query": "SELECT * FROM orders WHERE id = :order_id",
        "read_only": True,
        "parameter_mapping": {"order_id": "order_id"},
        "max_rows": 50,
    }
    config = parse_binding_config(payload)
    assert isinstance(config, SQLBindingConfig)
    assert config.read_only is True
    assert config.max_rows == 50


def test_binding_validation_rejects_invalid_type() -> None:
    with pytest.raises(ValueError, match="binding.type"):
        validate_binding_config({"type": "smtp"})


def test_binding_validation_rejects_plaintext_header_secret() -> None:
    with pytest.raises(ValueError, match="must use \\$\\{ENV_VAR\\} reference"):
        validate_binding_config(
            {
                "type": "http",
                "method": "GET",
                "url": "https://api.example.com",
                "headers": {"Authorization": "Bearer abc123"},
            }
        )


def test_binding_validation_rejects_non_parameterized_sql() -> None:
    with pytest.raises(ValueError, match="parameterized"):
        validate_binding_config(
            {
                "type": "sql",
                "connection": "${READ_DB_DSN}",
                "query": "SELECT * FROM orders WHERE id = 1",
            }
        )

