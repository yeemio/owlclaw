"""Local development environment asset checks."""

from __future__ import annotations

from pathlib import Path
import re

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
    assert "${OWLCLAW_PG_PORT:-5432}:5432" in postgres["ports"]
    assert "healthcheck" in postgres
    volumes = "\n".join(postgres.get("volumes", []))
    assert "init-test-db.sql" in volumes


def test_minimal_compose_uses_pgvector_and_persistent_volume() -> None:
    payload = _load_yaml(Path("docker-compose.minimal.yml"))
    services = payload["services"]
    db = services.get("owlclaw-db") or services.get("postgres")
    assert db is not None
    assert db["image"] == "pgvector/pgvector:pg16"
    assert db["environment"]["POSTGRES_DB"] in {"postgres", "owlclaw"}
    assert "${OWLCLAW_PG_PORT:-5432}:5432" in db["ports"]
    assert "owlclaw_minimal_data" in "\n".join(db.get("volumes", []))
    assert "healthcheck" in db


def test_dev_compose_contains_expected_services_and_healthchecks() -> None:
    payload = _load_yaml(Path("docker-compose.dev.yml"))
    services = payload["services"]
    assert services["owlclaw-db"]["image"] == "pgvector/pgvector:pg16"
    assert "${OWLCLAW_PG_PORT:-5432}:5432" in services["owlclaw-db"]["ports"]
    assert services["hatchet-lite"]["image"].startswith("ghcr.io/hatchet-dev/hatchet/hatchet-lite:")
    assert services["langfuse"]["image"] == "langfuse/langfuse:2"
    assert services["redis"]["image"] == "redis:7-alpine"
    assert "${OWLCLAW_REDIS_PORT:-6379}:6379" in services["redis"]["ports"]
    assert "${OWLCLAW_LANGFUSE_PORT:-3000}:3000" in services["langfuse"]["ports"]
    assert "http://$$HOSTNAME:3000/" in " ".join(services["langfuse"]["healthcheck"]["test"])
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
    assert "Windows" in payload and "PowerShell" in payload


def test_local_test_scripts_support_required_options() -> None:
    shell_payload = Path("scripts/test-local.sh").read_text(encoding="utf-8")
    ps_payload = Path("scripts/test-local.ps1").read_text(encoding="utf-8")
    assert "--unit-only" in shell_payload
    assert "--keep-up" in shell_payload
    assert "[switch]$unit_only" in ps_payload or "[switch]$UnitOnly" in ps_payload
    assert "[switch]$keep_up" in ps_payload or "[switch]$KeepUp" in ps_payload


def test_docs_cover_local_development_and_deployment() -> None:
    dev_doc = Path("docs/DEVELOPMENT.md").read_text(encoding="utf-8")
    deploy_doc = Path("docs/DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "快速开始（3 步）" in dev_doc
    assert "Windows" in dev_doc
    assert "pip install owlclaw" in deploy_doc
    assert "Docker" in deploy_doc and ("零 Docker 依赖" in deploy_doc or "不强依赖 Docker" in deploy_doc)


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
        "OWLCLAW_PG_PORT=5432",
        "OWLCLAW_REDIS_PORT=6379",
        "OWLCLAW_LANGFUSE_PORT=3000",
        "OWLCLAW_CONFIG=",
        "OWLCLAW_WEBHOOK_TIMEOUT_SECONDS=",
        "OWLCLAW_WEBHOOK_MAX_RETRIES=",
        "OWLCLAW_WEBHOOK_LOG_LEVEL=",
        "OWLCLAW_QDRANT_URL=",
        "OWLCLAW_QDRANT_COLLECTION=",
        "HATCHET_GRPC_TLS_STRATEGY=",
        "HATCHET_GRPC_HOST_PORT=",
        "OWLHUB_LOG_LEVEL=INFO",
        "OWLHUB_INDEX_PATH=./index.json",
        "OWLHUB_REVIEW_DIR=./.owlhub/reviews",
        "OWLHUB_AUDIT_LOG=./.owlhub/audit.log.jsonl",
        "OWLHUB_STATISTICS_DB=./.owlhub/skill_statistics.json",
        "OWLHUB_BLACKLIST_DB=./.owlhub/blacklist.json",
        "OWLHUB_AUTH_SECRET=",
        "OWLHUB_CSRF_TOKEN=",
    ]
    for key in expected:
        assert key in payload


def test_env_example_covers_literal_env_reads_in_owlclaw_code() -> None:
    ignored = {"PYTEST_CURRENT_TEST", "COV_CORE_SOURCE"}
    env_keys = {
        line.split("=", 1)[0].strip()
        for line in Path(".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    used_keys: set[str] = set()
    patterns = (
        re.compile(r'os\.getenv\(\s*"([A-Z][A-Z0-9_]*)"'),
        re.compile(r'os\.environ\.get\(\s*"([A-Z][A-Z0-9_]*)"'),
        re.compile(r'os\.environ\[\s*"([A-Z][A-Z0-9_]*)"\s*\]'),
    )
    for py_file in Path("owlclaw").rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for pattern in patterns:
            used_keys.update(pattern.findall(source))
    missing = sorted(key for key in used_keys if key not in env_keys and key not in ignored)
    assert missing == []
