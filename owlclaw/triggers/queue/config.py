"""Queue trigger configuration and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AckPolicy = Literal["ack", "nack", "requeue", "dlq"]
ParserType = Literal["json", "text", "binary"]


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

    return errors
