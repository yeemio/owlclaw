"""Shared test fixtures for OwlClaw."""

from pathlib import Path

import pytest

from owlclaw import OwlClaw

# Load .env from repo root so HATCHET_API_TOKEN etc. are set for integration tests
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    import dotenv
    dotenv.load_dotenv(_env_file)


@pytest.fixture
def app():
    """Create a test OwlClaw application."""
    return OwlClaw("test-app")
