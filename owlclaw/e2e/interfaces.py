"""Protocol interfaces for e2e validation components."""

from __future__ import annotations

from typing import Protocol

from owlclaw.e2e.models import ExecutionResult, TestScenario


class TestScenarioRepository(Protocol):
    """Persistent CRUD interface for test scenarios."""

    def create(self, scenario: TestScenario) -> None:
        """Persist a scenario."""

    def get(self, scenario_id: str) -> TestScenario | None:
        """Fetch one scenario by id."""

    def update(self, scenario: TestScenario) -> None:
        """Update an existing scenario."""

    def delete(self, scenario_id: str) -> bool:
        """Delete one scenario and return whether it existed."""

    def list_all(self) -> list[TestScenario]:
        """Return all scenarios."""


class ScenarioExecutionEngine(Protocol):
    """Execution interface for running one scenario."""

    async def execute_scenario(self, scenario: TestScenario) -> ExecutionResult:
        """Execute a scenario and return normalized result."""
