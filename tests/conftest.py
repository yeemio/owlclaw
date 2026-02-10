"""Shared test fixtures for OwlClaw."""

import pytest

from owlclaw import OwlClaw


@pytest.fixture
def app():
    """Create a test OwlClaw application."""
    return OwlClaw("test-app")
