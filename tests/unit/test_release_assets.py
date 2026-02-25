"""Release asset sanity checks."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py310 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def test_changelog_has_initial_release_section() -> None:
    payload = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0]" in payload
    assert "Initial public release candidate baseline." in payload


def test_issue_templates_exist() -> None:
    base = Path(".github/ISSUE_TEMPLATE")
    assert (base / "bug_report.yml").exists()
    assert (base / "feature_request.yml").exists()
    assert (base / "config.yml").exists()


def test_bug_report_template_has_required_core_fields() -> None:
    payload = yaml.safe_load(Path(".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8"))
    assert payload["name"] == "Bug Report"
    assert "bug" in payload["labels"]
    fields = [item.get("id") for item in payload["body"] if isinstance(item, dict)]
    assert "summary" in fields
    assert "reproduce" in fields
    assert "version" in fields


def test_gitignore_covers_release_sensitive_and_build_artifacts() -> None:
    payload = Path(".gitignore").read_text(encoding="utf-8")
    assert ".env" in payload
    assert "__pycache__/" in payload
    assert "dist/" in payload
    assert "build/" in payload
    assert "*.py[cod]" in payload


def test_env_example_uses_placeholders_only() -> None:
    payload = Path(".env.example").read_text(encoding="utf-8")
    assert "HATCHET_API_TOKEN=" in payload
    assert "LANGFUSE_SECRET_KEY=" in payload
    assert "sk-live-" not in payload
    assert "ghp_" not in payload


def test_pyproject_has_release_metadata_and_extras() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    poetry = payload["tool"]["poetry"]
    assert poetry["name"] == "owlclaw"
    assert poetry["version"] == "0.1.0"
    assert poetry["license"] == "MIT"
    assert "keywords" in poetry and isinstance(poetry["keywords"], list)
    assert "classifiers" in poetry and isinstance(poetry["classifiers"], list)

    extras = poetry["extras"]
    assert "langchain" in extras
    assert "dev" in extras
    assert "pytest" in extras["dev"]

    scripts = poetry["scripts"]
    assert scripts["owlclaw"] == "owlclaw.cli:main"


def test_owlclaw_mcp_standalone_package_config_exists() -> None:
    payload = tomllib.loads(Path("owlclaw-mcp/pyproject.toml").read_text(encoding="utf-8"))
    poetry = payload["tool"]["poetry"]
    assert poetry["name"] == "owlclaw-mcp"
    assert poetry["version"] == "0.1.0"
    scripts = poetry["scripts"]
    assert scripts["owlclaw-mcp"] == "owlclaw_mcp.server:main"
