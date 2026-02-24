"""Test data isolation utilities for e2e validation runs."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class IsolationContext:
    """Container for production and isolated test data snapshots."""

    production_snapshot: dict[str, Any]
    test_data: dict[str, Any]
    production_database_snapshot: dict[str, Any]
    test_database: dict[str, Any]
    production_config_snapshot: dict[str, Any]
    test_config: dict[str, Any]


class TestEnvironmentIsolation:
    """Manage isolated test data without mutating production snapshots."""

    __test__ = False

    def __init__(self) -> None:
        self._context: IsolationContext | None = None

    def create_isolation(
        self,
        production_data: dict[str, Any],
        *,
        production_database: dict[str, Any] | None = None,
        production_config: dict[str, Any] | None = None,
    ) -> IsolationContext:
        """Create isolated copy of production data for test execution."""
        snapshot = copy.deepcopy(production_data)
        test_data = copy.deepcopy(production_data)
        database_snapshot = copy.deepcopy(production_database or {})
        test_database = copy.deepcopy(production_database or {})
        config_snapshot = copy.deepcopy(production_config or {})
        test_config = copy.deepcopy(production_config or {})
        self._context = IsolationContext(
            production_snapshot=snapshot,
            test_data=test_data,
            production_database_snapshot=database_snapshot,
            test_database=test_database,
            production_config_snapshot=config_snapshot,
            test_config=test_config,
        )
        return self._context

    def write_test_data(self, key: str, value: Any) -> None:
        """Mutate isolated test data only."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        self._context.test_data[key] = value

    def read_test_data(self) -> dict[str, Any]:
        """Return isolated test data snapshot."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.test_data)

    def production_snapshot(self) -> dict[str, Any]:
        """Return production snapshot captured at isolation creation time."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.production_snapshot)

    def write_test_database(self, key: str, value: Any) -> None:
        """Mutate isolated test database only."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        self._context.test_database[key] = value

    def read_test_database(self) -> dict[str, Any]:
        """Return isolated test database snapshot."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.test_database)

    def production_database_snapshot(self) -> dict[str, Any]:
        """Return database snapshot captured at isolation creation time."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.production_database_snapshot)

    def update_test_config(self, key: str, value: Any) -> None:
        """Mutate isolated test configuration only."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        self._context.test_config[key] = value

    def read_test_config(self) -> dict[str, Any]:
        """Return isolated test configuration snapshot."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.test_config)

    def production_config_snapshot(self) -> dict[str, Any]:
        """Return configuration snapshot captured at isolation creation time."""
        if self._context is None:
            raise RuntimeError("create_isolation() must be called first")
        return copy.deepcopy(self._context.production_config_snapshot)

    @contextmanager
    def isolated_environment(
        self,
        production_data: dict[str, Any],
        *,
        production_database: dict[str, Any] | None = None,
        production_config: dict[str, Any] | None = None,
    ) -> Iterator[IsolationContext]:
        """Create isolated context for a test run and always cleanup afterward."""
        context = self.create_isolation(
            production_data,
            production_database=production_database,
            production_config=production_config,
        )
        try:
            yield context
        finally:
            self.cleanup()

    def is_active(self) -> bool:
        """Return whether an isolation context is currently active."""
        return self._context is not None

    def cleanup(self) -> None:
        """Clear isolated context."""
        self._context = None
