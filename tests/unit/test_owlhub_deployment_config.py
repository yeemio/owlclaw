"""Tests for OwlHub deployment configuration artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml(relative_path: str) -> dict:
    manifest = _repo_root() / relative_path
    assert manifest.exists()
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


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


def test_owlhub_k8s_deployment_contains_expected_pod_configuration() -> None:
    payload = _load_yaml("deploy/k8s/owlhub-api-deployment.yaml")
    assert payload["kind"] == "Deployment"
    assert payload["metadata"]["name"] == "owlhub-api"

    spec = payload["spec"]
    assert spec["selector"]["matchLabels"]["app"] == "owlhub-api"
    assert spec["replicas"] == 2

    container = spec["template"]["spec"]["containers"][0]
    assert container["name"] == "owlhub-api"
    assert container["ports"][0]["containerPort"] == 8000

    env_from = container.get("envFrom", [])
    config_ref = env_from[0]["configMapRef"]["name"]
    secret_ref = env_from[1]["secretRef"]["name"]
    assert config_ref == "owlhub-api-config"
    assert secret_ref == "owlhub-api-secret"

    assert container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert container["readinessProbe"]["httpGet"]["path"] == "/health"


def test_owlhub_k8s_service_exposes_http_port() -> None:
    payload = _load_yaml("deploy/k8s/owlhub-api-service.yaml")
    assert payload["kind"] == "Service"
    assert payload["metadata"]["name"] == "owlhub-api"

    spec = payload["spec"]
    assert spec["type"] == "ClusterIP"
    assert spec["selector"]["app"] == "owlhub-api"
    assert spec["ports"][0]["name"] == "http"
    assert spec["ports"][0]["port"] == 80
    assert spec["ports"][0]["targetPort"] == 8000


def test_owlhub_k8s_configmap_contains_runtime_configuration_keys() -> None:
    payload = _load_yaml("deploy/k8s/owlhub-api-configmap.yaml")
    assert payload["kind"] == "ConfigMap"
    assert payload["metadata"]["name"] == "owlhub-api-config"

    data = payload["data"]
    assert "OWLHUB_LOG_LEVEL" in data
    assert "OWLHUB_INDEX_PATH" in data
    assert "OWLHUB_REVIEW_DIR" in data
    assert "OWLHUB_AUDIT_LOG" in data
    assert "OWLHUB_STATISTICS_DB" in data
    assert "OWLHUB_BLACKLIST_DB" in data


def test_owlhub_k8s_secret_template_contains_required_keys() -> None:
    payload = _load_yaml("deploy/k8s/owlhub-api-secret.yaml")
    assert payload["kind"] == "Secret"
    assert payload["metadata"]["name"] == "owlhub-api-secret"
    assert payload["type"] == "Opaque"

    data = payload["stringData"]
    assert "OWLCLAW_DATABASE_URL" in data
    assert "OWLHUB_REDIS_URL" in data


def test_owlhub_k8s_ingress_routes_root_to_owlhub_service() -> None:
    payload = _load_yaml("deploy/k8s/owlhub-api-ingress.yaml")
    assert payload["kind"] == "Ingress"
    assert payload["metadata"]["name"] == "owlhub-api"

    rule = payload["spec"]["rules"][0]
    assert rule["host"] == "owlhub.local"
    path = rule["http"]["paths"][0]
    assert path["path"] == "/"
    assert path["pathType"] == "Prefix"
    service = path["backend"]["service"]
    assert service["name"] == "owlhub-api"
    assert service["port"]["number"] == 80
