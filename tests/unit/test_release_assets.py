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


def test_readme_has_release_required_sections() -> None:
    payload = Path("README.md").read_text(encoding="utf-8")
    assert "## What is OwlClaw?" in payload
    assert "## Quick Start" in payload
    assert "## Architecture Overview (ASCII)" in payload
    assert "## OwlClaw and LangChain/LangGraph" in payload
    assert "## Useful Links" in payload


def test_contributing_has_pr_and_style_guidance() -> None:
    payload = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "## Pull Request Guidelines" in payload
    assert "## Code Style" in payload


def test_release_runbook_exists_for_external_steps() -> None:
    payload = Path("docs/RELEASE_RUNBOOK.md").read_text(encoding="utf-8")
    assert "Configure Trusted Publishing (OIDC)" in payload
    assert "Dry-run To TestPyPI" in payload
    assert "Production Release" in payload
    assert "release_oidc_preflight.py" in payload


def test_trusted_publisher_setup_doc_has_required_fields() -> None:
    payload = Path("docs/release/TRUSTED_PUBLISHER_SETUP.md").read_text(encoding="utf-8")
    assert "Owner: `yeemio`" in payload
    assert "Repository name: `owlclaw`" in payload
    assert "Workflow filename: `.github/workflows/release.yml`" in payload


def test_release_workflow_is_tag_triggered() -> None:
    payload = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    on_cfg = payload.get("on", payload.get(True, {}))
    push_cfg = on_cfg.get("push", {})
    tags = push_cfg.get("tags", [])
    assert "v*" in tags
    dispatch_cfg = on_cfg.get("workflow_dispatch", {})
    assert "inputs" in dispatch_cfg
    target_cfg = dispatch_cfg["inputs"]["target"]
    assert target_cfg["default"] == "testpypi"
    assert "testpypi" in target_cfg["options"]
    assert "pypi" in target_cfg["options"]


def test_release_workflow_supports_testpypi_and_pypi_publish_steps() -> None:
    payload = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "Publish to TestPyPI" in payload
    assert "pypa/gh-action-pypi-publish@release/v1" in payload
    assert "https://test.pypi.org/legacy/" in payload
    assert "Publish to PyPI" in payload
    assert "secrets.TEST_PYPI_TOKEN" not in payload
    assert "secrets.PYPI_TOKEN" not in payload
