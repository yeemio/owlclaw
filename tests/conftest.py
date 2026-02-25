"""Shared test fixtures and collection-time service gating for OwlClaw."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest

from owlclaw import OwlClaw

# Load .env from repo root so HATCHET_API_TOKEN etc. are set for integration tests
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    import dotenv

    dotenv.load_dotenv(_env_file)


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True when host:port accepts TCP connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def _host_port_from_url(url: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return host, port


def _infer_runtime_markers(item: pytest.Item) -> set[str]:
    """Infer service requirements from node id to reduce per-file marker boilerplate."""
    nodeid = item.nodeid.lower()
    inferred: set[str] = set()

    # Keep unit tests strict: only infer external service requirements in integration suite.
    if "tests/integration/" not in nodeid.replace("\\", "/"):
        return inferred

    if "hatchet" in nodeid:
        inferred.add("requires_hatchet")
    if "kafka" in nodeid:
        inferred.add("requires_kafka")
    if "redis" in nodeid or "idempotency" in nodeid:
        inferred.add("requires_redis")

    return inferred


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip service-dependent tests when required services are unavailable."""
    hatchet_url = os.getenv("HATCHET_SERVER_URL", "http://localhost:17077")
    hatchet_host, hatchet_port = _host_port_from_url(hatchet_url, default_port=17077)

    service_available = {
        "requires_postgres": _is_port_open("localhost", 5432),
        "requires_hatchet": _is_port_open(hatchet_host, hatchet_port),
        "requires_redis": _is_port_open("localhost", 6379),
        "requires_kafka": _is_port_open("localhost", 9092),
    }

    reasons = {
        "requires_postgres": "PostgreSQL is not available on localhost:5432",
        "requires_hatchet": f"Hatchet is not available on {hatchet_host}:{hatchet_port}",
        "requires_redis": "Redis is not available on localhost:6379",
        "requires_kafka": "Kafka is not available on localhost:9092",
    }

    for item in items:
        required = {mark.name for mark in item.iter_markers() if mark.name in service_available}
        required.update(_infer_runtime_markers(item))
        for marker in sorted(required):
            if not service_available[marker]:
                item.add_marker(pytest.mark.skip(reason=reasons[marker]))


@pytest.fixture
def app():
    """Create a test OwlClaw application."""
    return OwlClaw("test-app")
