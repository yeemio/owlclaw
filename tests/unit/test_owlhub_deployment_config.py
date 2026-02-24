"""Tests for OwlHub deployment configuration artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_owlhub_api_dockerfile_contains_expected_runtime_command() -> None:
    dockerfile = _repo_root() / "deploy" / "Dockerfile.owlhub-api"
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")
    assert "poetry install --only main --extras api" in content
    assert "uvicorn" in content
    assert "owlclaw.owlhub.api.app:create_app" in content
    assert "--factory" in content
    assert "EXPOSE 8000" in content


def test_owlhub_compose_contains_api_postgres_and_redis_services() -> None:
    compose_file = _repo_root() / "deploy" / "docker-compose.owlhub-api.yml"
    assert compose_file.exists()
    payload = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    services = payload.get("services", {})
    assert isinstance(services, dict)
    assert "owlhub-api" in services
    assert "postgres" in services
    assert "redis" in services

    api = services["owlhub-api"]
    assert api["build"]["dockerfile"] == "deploy/Dockerfile.owlhub-api"
    env = api.get("environment", {})
    assert "OWLHUB_INDEX_PATH" in env
    assert "OWLHUB_REVIEW_DIR" in env
    assert "OWLHUB_STATISTICS_DB" in env
    assert "OWLHUB_BLACKLIST_DB" in env
    assert "OWLHUB_LOG_LEVEL" in env
    assert "OWLCLAW_DATABASE_URL" in env
    assert "OWLHUB_REDIS_URL" in env

    postgres = services["postgres"]
    assert "postgres:15-alpine" in postgres.get("image", "")
    redis = services["redis"]
    assert redis.get("profiles") == ["redis"]
