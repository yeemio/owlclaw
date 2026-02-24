"""Configuration models for database change trigger."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DBChangeTriggerConfig(BaseModel):
    """Configuration for one db change trigger registration."""

    tenant_id: str = "default"
    channel: str
    event_name: str
    agent_id: str
    debounce_seconds: float | None = Field(default=None, ge=0)
    batch_size: int | None = Field(default=None, ge=1)
    focus: str | None = None
    source: str = "notify"

    @field_validator("tenant_id", "channel", "event_name", "agent_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized
