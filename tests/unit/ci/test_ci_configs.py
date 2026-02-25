"""Validation tests for CI/CD configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_lint_workflow_contains_ruff_and_mypy_steps() -> None:
    payload = _load_yaml(Path(".github/workflows/lint.yml"))
    jobs = payload.get("jobs", {})
    assert "lint" in jobs
    steps = jobs["lint"]["steps"]
    step_text = "\n".join(str(item) for item in steps)
    assert "ruff check ." in step_text
    assert "mypy owlclaw --strict" in step_text


def test_test_workflow_has_python_matrix_and_postgres_service() -> None:
    payload = _load_yaml(Path(".github/workflows/test.yml"))
    jobs = payload.get("jobs", {})
    assert "test" in jobs
    matrix = jobs["test"]["strategy"]["matrix"]["python-version"]
    assert matrix == ["3.10", "3.11", "3.12"]
    postgres = jobs["test"]["services"]["postgres"]
    assert postgres["image"] == "postgres:16"
    steps = "\n".join(str(item) for item in jobs["test"]["steps"])
    assert "--cov-fail-under=80" in steps


def test_build_workflow_contains_build_and_twine_check() -> None:
    payload = _load_yaml(Path(".github/workflows/build.yml"))
    jobs = payload.get("jobs", {})
    assert "build" in jobs
    steps = "\n".join(str(item) for item in jobs["build"]["steps"])
    assert "python -m build" in steps
    assert "twine check dist/*" in steps


def test_release_workflow_contains_release_commands() -> None:
    payload = _load_yaml(Path(".github/workflows/release.yml"))
    jobs = payload.get("jobs", {})
    assert "release" in jobs
    steps = "\n".join(str(item) for item in jobs["release"]["steps"])
    assert "semantic-release version" in steps
    assert "semantic-release publish" in steps
    assert "twine upload dist/*" in steps


def test_releaserc_contains_required_plugins() -> None:
    payload = json.loads(Path(".releaserc.json").read_text(encoding="utf-8"))
    plugins = payload.get("plugins", [])
    as_text = json.dumps(plugins)
    assert "@semantic-release/commit-analyzer" in as_text
    assert "@semantic-release/release-notes-generator" in as_text
    assert "@semantic-release/changelog" in as_text
    assert "@semantic-release/exec" in as_text
    assert "@semantic-release/git" in as_text
    assert "@semantic-release/github" in as_text


def test_pre_commit_config_contains_required_hooks() -> None:
    payload = _load_yaml(Path(".pre-commit-config.yaml"))
    repos = payload.get("repos", [])
    flattened = "\n".join(str(item) for item in repos)
    assert "ruff" in flattened
    assert "ruff-format" in flattened
    assert "mypy" in flattened
    assert "trailing-whitespace" in flattened
    assert "end-of-file-fixer" in flattened
    assert "check-yaml" in flattened


def test_dependabot_config_contains_pip_and_actions() -> None:
    payload = _load_yaml(Path(".github/dependabot.yml"))
    updates = payload.get("updates", [])
    ecosystems = {entry["package-ecosystem"] for entry in updates}
    assert ecosystems == {"pip", "github-actions"}
