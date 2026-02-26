"""Baseline checks for cross-language Java golden path assets."""

from __future__ import annotations

from pathlib import Path


def test_java_golden_path_project_structure_exists() -> None:
    root = Path("examples/cross_lang/java")
    assert (root / "pom.xml").exists()
    assert (root / "README.md").exists()
    assert (root / "src/main/java/dev/owlclaw/examples/OwlClawApiClient.java").exists()


def test_java_client_includes_trigger_and_query_methods() -> None:
    payload = Path("examples/cross_lang/java/src/main/java/dev/owlclaw/examples/OwlClawApiClient.java").read_text(
        encoding="utf-8"
    )
    assert "triggerAgent(" in payload
    assert "queryStatus(" in payload
