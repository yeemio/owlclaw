"""Unit tests for e2e core models and interfaces."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlclaw.e2e.models import (
    ExecutionResult,
    ExecutionStatus,
    ScenarioType,
    ValidationConfig,
)
from owlclaw.e2e.models import (
    TestScenario as E2ETestScenario,
)


def test_test_scenario_defaults() -> None:
    scenario = E2ETestScenario(
        scenario_id="s1",
        name="Scenario 1",
        scenario_type=ScenarioType.INTEGRATION,
    )
    assert scenario.timeout_seconds == 300
    assert scenario.input_data == {}
    assert scenario.expected_outcomes == {}
    assert scenario.tags == []


def test_execution_result_requires_non_negative_duration() -> None:
    with pytest.raises(ValidationError):
        ExecutionResult(
            scenario_id="s1",
            status=ExecutionStatus.PASSED,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            duration_ms=-1.0,
        )


def test_validation_config_enforces_positive_limits() -> None:
    with pytest.raises(ValidationError):
        ValidationConfig(max_parallel_runs=0)
