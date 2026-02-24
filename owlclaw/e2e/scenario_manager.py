"""Scenario management for e2e validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from owlclaw.e2e.models import TestScenario


class TestScenarioManager:
    """Manage lifecycle of test scenarios with optional JSON persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self._storage_path = Path(storage_path) if storage_path else None
        self._scenarios: dict[str, TestScenario] = {}
        self._load()

    def create_scenario(self, scenario: TestScenario) -> str:
        """Create a new scenario and return its id."""
        errors = self.validate_scenario(scenario)
        if errors:
            raise ValueError("; ".join(errors))
        if scenario.scenario_id in self._scenarios:
            raise ValueError(f"Scenario '{scenario.scenario_id}' already exists")
        self._scenarios[scenario.scenario_id] = scenario
        self._persist()
        return scenario.scenario_id

    def get_scenario(self, scenario_id: str) -> TestScenario | None:
        """Return a scenario by id."""
        return self._scenarios.get(scenario_id)

    def update_scenario(self, scenario_id: str, updates: TestScenario) -> None:
        """Update one scenario by replacing with validated content."""
        if scenario_id not in self._scenarios:
            raise KeyError(f"Scenario '{scenario_id}' not found")
        if updates.scenario_id != scenario_id:
            raise ValueError("scenario_id in updates must match target scenario_id")
        errors = self.validate_scenario(updates)
        if errors:
            raise ValueError("; ".join(errors))
        self._scenarios[scenario_id] = updates
        self._persist()

    def delete_scenario(self, scenario_id: str) -> None:
        """Delete one scenario."""
        if scenario_id not in self._scenarios:
            raise KeyError(f"Scenario '{scenario_id}' not found")
        del self._scenarios[scenario_id]
        self._persist()

    def list_scenarios(self) -> list[TestScenario]:
        """List all scenarios."""
        return list(self._scenarios.values())

    def export_scenarios(self, scenario_ids: list[str] | None = None) -> str:
        """Export selected scenarios as JSON text."""
        if scenario_ids is None:
            selected = self.list_scenarios()
        else:
            selected = []
            for scenario_id in scenario_ids:
                scenario = self.get_scenario(scenario_id)
                if scenario is None:
                    raise KeyError(f"Scenario '{scenario_id}' not found")
                selected.append(scenario)
        payload = [scenario.model_dump(mode="json") for scenario in selected]
        return json.dumps(payload, ensure_ascii=False)

    def import_scenarios(self, data: str) -> list[str]:
        """Import scenarios from JSON text and upsert by scenario_id."""
        parsed = json.loads(data)
        if not isinstance(parsed, list):
            raise ValueError("Scenario import payload must be a list")

        imported_ids: list[str] = []
        for item in parsed:
            scenario = TestScenario.model_validate(item)
            errors = self.validate_scenario(scenario)
            if errors:
                raise ValueError("; ".join(errors))
            self._scenarios[scenario.scenario_id] = scenario
            imported_ids.append(scenario.scenario_id)

        self._persist()
        return imported_ids

    @staticmethod
    def validate_scenario(scenario: TestScenario) -> list[str]:
        """Validate a normalized scenario model."""
        errors: list[str] = []
        if not scenario.scenario_id.strip():
            errors.append("scenario_id must be non-empty")
        if not scenario.name.strip():
            errors.append("name must be non-empty")
        if scenario.timeout_seconds < 1:
            errors.append("timeout_seconds must be >= 1")
        return errors

    @staticmethod
    def validate_scenario_payload(payload: dict[str, Any]) -> list[str]:
        """Validate raw payload using model schema and business constraints."""
        try:
            scenario = TestScenario.model_validate(payload)
        except ValidationError as exc:
            return [f"{'.'.join(str(v) for v in error['loc'])}: {error['msg']}" for error in exc.errors()]
        return TestScenarioManager.validate_scenario(scenario)

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Scenario storage must be a list")
        for item in raw:
            scenario = TestScenario.model_validate(item)
            self._scenarios[scenario.scenario_id] = scenario

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [scenario.model_dump(mode="json") for scenario in self._scenarios.values()]
        self._storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
