"""Local development environment asset checks."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_root_compose_files_exist() -> None:
    assert Path("docker-compose.test.yml").exists()
    assert Path("docker-compose.minimal.yml").exists()
    assert Path("docker-compose.dev.yml").exists()


def test_test_compose_mirrors_ci_pgvector_setup() -> None:
    payload = _load_yaml(Path("docker-compose.test.yml"))
    postgres = payload["services"]["postgres"]
    assert postgres["image"] == "pgvector/pgvector:pg16"
    assert postgres["environment"]["POSTGRES_DB"] == "owlclaw_test"
    assert "healthcheck" in postgres
    volumes = "\n".join(postgres.get("volumes", []))
    assert "init-test-db.sql" in volumes


def test_minimal_compose_uses_pgvector_and_persistent_volume() -> None:
    payload = _load_yaml(Path("docker-compose.minimal.yml"))
    db = payload["services"]["owlclaw-db"]
    assert db["image"] == "pgvector/pgvector:pg16"
    assert db["environment"]["POSTGRES_DB"] == "owlclaw"
    assert "owlclaw_minimal_data" in "\n".join(db.get("volumes", []))
    assert "healthcheck" in db


def test_dev_compose_contains_expected_services_and_healthchecks() -> None:
    payload = _load_yaml(Path("docker-compose.dev.yml"))
    services = payload["services"]
    assert services["owlclaw-db"]["image"] == "pgvector/pgvector:pg16"
    assert services["hatchet-lite"]["image"] == "ghcr.io/hatchet-dev/hatchet/hatchet-lite:v0.53.0"
    assert services["langfuse"]["image"] == "langfuse/langfuse:2"
    assert services["redis"]["image"] == "redis:7-alpine"
    assert all("healthcheck" in services[name] for name in ("owlclaw-db", "hatchet-lite", "langfuse", "redis"))


def test_deploy_compose_files_are_pgvector_aligned() -> None:
    for compose in (
        Path("deploy/docker-compose.lite.yml"),
        Path("deploy/docker-compose.prod.yml"),
        Path("deploy/docker-compose.cron.yml"),
    ):
        payload = _load_yaml(compose)
        assert payload["services"]["owlclaw-db"]["image"] == "pgvector/pgvector:pg16"


def test_init_db_creates_langfuse_database_and_vector_extension() -> None:
    payload = Path("deploy/init-db.sql").read_text(encoding="utf-8")
    assert "CREATE DATABASE langfuse;" in payload
    assert "CREATE ROLE langfuse" in payload
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in payload


def test_makefile_has_required_targets() -> None:
    payload = Path("Makefile").read_text(encoding="utf-8")
    for target in (
        "dev-up:",
        "dev-down:",
        "dev-reset:",
        "test-up:",
        "test-down:",
        "test:",
        "test-unit:",
        "test-int:",
        "lint:",
        "typecheck:",
    ):
        assert target in payload
    assert "Windows PowerShell equivalents" in payload


def test_local_test_scripts_support_required_options() -> None:
    shell_payload = Path("scripts/test-local.sh").read_text(encoding="utf-8")
    ps_payload = Path("scripts/test-local.ps1").read_text(encoding="utf-8")
    assert "--unit-only" in shell_payload
    assert "--keep-up" in shell_payload
    assert "[switch]$UnitOnly" in ps_payload
    assert "[switch]$KeepUp" in ps_payload


def test_docs_cover_local_development_and_deployment() -> None:
    dev_doc = Path("docs/DEVELOPMENT.md").read_text(encoding="utf-8")
    deploy_doc = Path("docs/DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "快速开始（3 步）" in dev_doc
    assert "Windows" in dev_doc
    assert "pip install owlclaw" in deploy_doc
    assert "零 Docker 依赖" in deploy_doc


def test_env_example_covers_local_devenv_core_variables() -> None:
    payload = Path(".env.example").read_text(encoding="utf-8")
    expected = [
        "DATABASE_URL=",
        "OWLCLAW_DATABASE_URL=",
        "HATCHET_API_TOKEN=",
        "HATCHET_SERVER_URL=",
        "LANGFUSE_HOST=http://localhost:3000",
        "REDIS_URL=redis://localhost:6379/0",
        "KAFKA_BOOTSTRAP_SERVERS=",
    ]
    for key in expected:
        assert key in payload
