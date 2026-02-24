"""Unit and property tests for e2e test data isolation."""

from __future__ import annotations

import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.e2e.test_isolation import TestEnvironmentIsolation


class TestTestEnvironmentIsolation:
    def test_create_isolation_with_database_and_config(self) -> None:
        production_data = {"account": {"balance": 100}}
        production_database = {"orders": {"o1": "open"}}
        production_config = {"timeout_seconds": 30, "retry": 1}

        isolation = TestEnvironmentIsolation()
        isolation.create_isolation(
            production_data,
            production_database=production_database,
            production_config=production_config,
        )

        isolation.write_test_data("new_field", {"value": "test-only"})
        isolation.write_test_database("orders", {"o1": "closed"})
        isolation.update_test_config("timeout_seconds", 5)

        assert isolation.production_snapshot() == production_data
        assert isolation.production_database_snapshot() == production_database
        assert isolation.production_config_snapshot() == production_config
        assert isolation.read_test_data()["new_field"] == {"value": "test-only"}
        assert isolation.read_test_database()["orders"] == {"o1": "closed"}
        assert isolation.read_test_config()["timeout_seconds"] == 5

    def test_isolated_environment_context_manager_auto_cleanup(self) -> None:
        isolation = TestEnvironmentIsolation()
        with isolation.isolated_environment({"a": 1}, production_database={"db": 1}, production_config={"cfg": 1}):
            assert isolation.is_active() is True
            isolation.write_test_data("a", 2)
        assert isolation.is_active() is False
        with pytest.raises(RuntimeError):
            isolation.read_test_data()


class TestIsolationProperties:
    @settings(max_examples=100, deadline=None)
    @given(
        production_data=st.dictionaries(
            st.text(min_size=1, max_size=8),
            st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=16)),
            max_size=6,
        ),
        production_database=st.dictionaries(
            st.text(min_size=1, max_size=8),
            st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=4),
            max_size=4,
        ),
        production_config=st.dictionaries(
            st.text(min_size=1, max_size=12),
            st.one_of(st.booleans(), st.integers(), st.text(max_size=12)),
            max_size=6,
        ),
        key=st.text(min_size=1, max_size=10),
        value=st.one_of(st.integers(), st.text(max_size=16), st.booleans()),
    )
    def test_property_test_data_isolation(
        self,
        production_data: dict[str, object],
        production_database: dict[str, dict[str, int]],
        production_config: dict[str, object],
        key: str,
        value: object,
    ) -> None:
        """Property 13: test-side writes never mutate production snapshots."""
        data_before = copy.deepcopy(production_data)
        database_before = copy.deepcopy(production_database)
        config_before = copy.deepcopy(production_config)

        isolation = TestEnvironmentIsolation()
        isolation.create_isolation(
            production_data,
            production_database=production_database,
            production_config=production_config,
        )
        isolation.write_test_data(key, value)
        isolation.write_test_database(key, {"isolated": 1})
        isolation.update_test_config(key, value)

        assert isolation.production_snapshot() == data_before
        assert isolation.production_database_snapshot() == database_before
        assert isolation.production_config_snapshot() == config_before
        assert production_data == data_before
        assert production_database == database_before
        assert production_config == config_before
