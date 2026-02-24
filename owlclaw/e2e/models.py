"""Core data models for end-to-end validation workflows."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    """Supported scenario classes for validation runs."""

    MIONYEE_TASK = "mionyee_task"
    DECISION_COMPARISON = "decision_comparison"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    CONCURRENCY = "concurrency"


class ExecutionStatus(str, Enum):
    """Execution outcome state."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestScenario(BaseModel):
    """Definition of a single runnable validation scenario."""

    scenario_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    scenario_type: ScenarioType
    input_data: dict[str, Any] = Field(default_factory=dict)
    expected_outcomes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=300, ge=1)


class ExecutionEvent(BaseModel):
    """Structured event emitted during scenario execution."""

    timestamp: datetime
    event_type: str = Field(..., min_length=1)
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Normalized result payload for one scenario execution."""

    scenario_id: str = Field(..., min_length=1)
    status: ExecutionStatus
    started_at: datetime
    ended_at: datetime
    duration_ms: float = Field(..., ge=0)
    events: list[ExecutionEvent] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationConfig(BaseModel):
    """Runtime configuration for e2e validation execution."""

    max_parallel_runs: int = Field(default=1, ge=1)
    default_timeout_seconds: int = Field(default=300, ge=1)
    collect_metrics: bool = True
    collect_events: bool = True
    output_dir: str = ".kiro/reports/e2e"
    fail_fast: bool = False
