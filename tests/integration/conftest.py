"""Integration test defaults."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_postgres


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply default PostgreSQL requirement marker to all integration tests."""
    for item in items:
        item.add_marker(pytest.mark.requires_postgres)
