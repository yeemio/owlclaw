"""Release asset presence checks."""

from __future__ import annotations

from pathlib import Path


def test_release_assets_exist() -> None:
    repo = Path(__file__).resolve().parents[2]
    required = [
        repo / "CHANGELOG.md",
        repo / "CONTRIBUTING.md",
        repo / ".github" / "workflows" / "release.yml",
        repo / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
        repo / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
        repo / "docs" / "release" / "SECURITY_SCAN_REPORT.md",
        repo / "docs" / "release" / "CREDENTIAL_AUDIT.md",
    ]
    for path in required:
        assert path.exists(), f"missing release asset: {path}"
        assert path.read_text(encoding="utf-8").strip(), f"empty release asset: {path}"
