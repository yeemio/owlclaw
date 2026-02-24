"""Tests for TestScenarioManager."""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.models import ScenarioType
from owlclaw.e2e.models import TestScenario as E2ETestScenario
from owlclaw.e2e.scenario_manager import TestScenarioManager as E2EScenarioManager


def _scenario_strategy() -> st.SearchStrategy[E2ETestScenario]:
    return st.builds(
        E2ETestScenario,
        scenario_id=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=1,
            max_size=20,
        ),
        name=st.text(min_size=1, max_size=50),
        description=st.text(max_size=100),
        scenario_type=st.sampled_from(list(ScenarioType)),
        input_data=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
        expected_outcomes=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
        tags=st.lists(st.text(min_size=1, max_size=10), max_size=3),
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )


class TestScenarioManagerUnit:
    def test_create_get_update_delete(self) -> None:
        manager = E2EScenarioManager()
        scenario = E2ETestScenario(
            scenario_id="s1",
            name="scenario",
            scenario_type=ScenarioType.INTEGRATION,
        )
        scenario_id = manager.create_scenario(scenario)
        assert scenario_id == "s1"
        assert manager.get_scenario("s1") == scenario

        updated = scenario.model_copy(update={"name": "updated"})
        manager.update_scenario("s1", updated)
        assert manager.get_scenario("s1") == updated

        manager.delete_scenario("s1")
        assert manager.get_scenario("s1") is None

    def test_validate_scenario_payload_returns_errors(self) -> None:
        payload: dict[str, Any] = {
            "scenario_id": "",
            "name": "",
            "scenario_type": "integration",
            "timeout_seconds": 0,
        }
        errors = E2EScenarioManager.validate_scenario_payload(payload)
        assert errors


class TestScenarioManagerProperties:
    @settings(max_examples=100, deadline=None)
    @given(scenario=_scenario_strategy())
    def test_property_scenario_crud_roundtrip(self, scenario: E2ETestScenario) -> None:
        """Property 11: CRUD roundtrip keeps scenario equivalence."""
        manager = E2EScenarioManager()
        created_id = manager.create_scenario(scenario)
        assert created_id == scenario.scenario_id
        fetched = manager.get_scenario(scenario.scenario_id)
        assert fetched == scenario

        updated = scenario.model_copy(update={"name": f"{scenario.name}-updated"})
        manager.update_scenario(scenario.scenario_id, updated)
        assert manager.get_scenario(scenario.scenario_id) == updated

        manager.delete_scenario(scenario.scenario_id)
        assert manager.get_scenario(scenario.scenario_id) is None

    @settings(max_examples=100, deadline=None)
    @given(
        bad_id=st.sampled_from(["", "   "]),
        bad_name=st.sampled_from(["", "   "]),
        bad_timeout=st.integers(max_value=0),
    )
    def test_property_invalid_payload_is_rejected(
        self,
        bad_id: str,
        bad_name: str,
        bad_timeout: int,
    ) -> None:
        """Property 12: invalid config returns validation errors."""
        payload: dict[str, Any] = {
            "scenario_id": bad_id,
            "name": bad_name,
            "scenario_type": "integration",
            "timeout_seconds": bad_timeout,
        }
        errors = E2EScenarioManager.validate_scenario_payload(payload)
        assert len(errors) >= 1
