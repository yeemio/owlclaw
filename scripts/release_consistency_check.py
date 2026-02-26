"""Check local release consistency before external publish."""

from __future__ import annotations

import re
from pathlib import Path


def check_consistency(repo: Path) -> int:
    pyproject = repo / "pyproject.toml"
    changelog = repo / "CHANGELOG.md"
    release_workflow = repo / ".github" / "workflows" / "release.yml"

    if not pyproject.exists() or not changelog.exists() or not release_workflow.exists():
        print("missing required files")
        return 2

    version = _extract_poetry_version(pyproject.read_text(encoding="utf-8"))
    if not version:
        print("failed to parse version from pyproject.toml")
        return 2
    changelog_text = changelog.read_text(encoding="utf-8")
    workflow_text = release_workflow.read_text(encoding="utf-8")

    if f"## [{version}] " not in changelog_text:
        print(f"changelog missing version section: {version}")
        return 2
    if "notes-file CHANGELOG.md" not in workflow_text:
        print("release workflow does not use changelog notes file")
        return 2
    if "pyproject.toml" not in workflow_text:
        print("release workflow does not derive version from pyproject.toml")
        return 2

    print(f"release_consistency_ok=true version={version}")
    return 0


def _extract_poetry_version(pyproject_text: str) -> str | None:
    in_poetry_section = False
    for raw_line in pyproject_text.splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_poetry_section = line == "[tool.poetry]"
            continue
        if in_poetry_section and line.startswith("version"):
            match = re.match(r'version\s*=\s*"([^"]+)"', line)
            if match:
                return match.group(1)
    return None


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    raise SystemExit(check_consistency(repo))


if __name__ == "__main__":
    main()
