"""Queue trigger configuration and validation helpers."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml  # type: ignore[import-untyped]

AckPolicy = Literal["ack", "nack", "requeue", "dlq"]
ParserType = Literal["json", "text", "binary"]
VALID_ACK_POLICIES: set[str] = {"ack", "nack", "requeue", "dlq"}
VALID_PARSER_TYPES: set[str] = {"json", "text", "binary"}


@dataclass(slots=True)
class QueueTriggerConfig:
    """Queue trigger runtime configuration."""

    queue_name: str
    consumer_group: str
    concurrency: int = 1
    ack_policy: AckPolicy = "ack"
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    retry_backoff_multiplier: float = 2.0
    idempotency_window: int = 3600
    enable_dedup: bool = True
    parser_type: ParserType = "json"
    event_name_header: str = "x-event-name"
    focus: str | None = None


def validate_config(config: QueueTriggerConfig) -> list[str]:
    """Validate queue trigger configuration and return error messages."""
    errors: list[str] = []

    if not config.queue_name.strip():
        errors.append("queue_name is required")
    if not config.consumer_group.strip():
        errors.append("consumer_group is required")
    if config.concurrency <= 0:
        errors.append("concurrency must be positive")
    if config.max_retries < 0:
        errors.append("max_retries must be non-negative")
    if config.retry_backoff_base <= 0:
        errors.append("retry_backoff_base must be positive")
    if config.retry_backoff_multiplier < 1.0:
        errors.append("retry_backoff_multiplier must be >= 1")
    if config.idempotency_window <= 0:
        errors.append("idempotency_window must be positive")
    if config.ack_policy not in VALID_ACK_POLICIES:
        errors.append(f"ack_policy must be one of {sorted(VALID_ACK_POLICIES)}")
    if config.parser_type not in VALID_PARSER_TYPES:
        errors.append(f"parser_type must be one of {sorted(VALID_PARSER_TYPES)}")

    return errors


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _replace_env_vars(value: Any) -> Any:
    """Recursively replace ${ENV_VAR} placeholders using process env."""
    if isinstance(value, dict):
        return {k: _replace_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_env_vars(v) for v in value]
    if not isinstance(value, str):
        return value

    def _lookup(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return _ENV_PATTERN.sub(_lookup, value)


def _require_str(config_map: dict[str, Any], key: str, default: str) -> str:
    value = config_map.get(key, default)
    if value is None:
        return default
    return str(value)


def _require_int(config_map: dict[str, Any], key: str, default: int) -> int:
    value = config_map.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _require_float(config_map: dict[str, Any], key: str, default: float) -> float:
    value = config_map.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number") from exc


def _coerce_bool(config_map: dict[str, Any], key: str, default: bool) -> bool:
    value = config_map.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def load_queue_trigger_config(config_path: str) -> QueueTriggerConfig:
    """Load queue trigger config from YAML file and validate it."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Queue trigger config root must be a mapping")

    config_map = raw.get("queue_trigger", raw)
    if not isinstance(config_map, dict):
        raise ValueError("queue_trigger section must be a mapping")
    config_map = _replace_env_vars(config_map)
    if not isinstance(config_map, dict):
        raise ValueError("queue_trigger section must be a mapping")
    config_dict = cast(dict[str, Any], config_map)

    config = QueueTriggerConfig(
        queue_name=_require_str(config_dict, "queue_name", ""),
        consumer_group=_require_str(config_dict, "consumer_group", ""),
        concurrency=_require_int(config_dict, "concurrency", 1),
        ack_policy=cast(AckPolicy, _require_str(config_dict, "ack_policy", "ack")),
        max_retries=_require_int(config_dict, "max_retries", 3),
        retry_backoff_base=_require_float(config_dict, "retry_backoff_base", 1.0),
        retry_backoff_multiplier=_require_float(config_dict, "retry_backoff_multiplier", 2.0),
        idempotency_window=_require_int(config_dict, "idempotency_window", 3600),
        enable_dedup=_coerce_bool(config_dict, "enable_dedup", True),
        parser_type=cast(ParserType, _require_str(config_dict, "parser_type", "json")),
        event_name_header=_require_str(config_dict, "event_name_header", "x-event-name"),
        focus=(None if config_dict.get("focus") is None else str(config_dict.get("focus"))),
    )

    errors = validate_config(config)
    if errors:
        raise ValueError(f"Invalid queue trigger config: {'; '.join(errors)}")
    return config
