"""Architecture isolation checks for web API layer."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "owlclaw.agent",
    "owlclaw.governance",
    "owlclaw.triggers",
    "owlclaw.capabilities",
)
API_DIR = Path("owlclaw/web/api")


def _import_name_from_node(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.module:
            return [node.module]
    return []


def test_web_api_has_no_direct_imports_from_forbidden_layers() -> None:
    violations: list[str] = []
    for file_path in sorted(API_DIR.glob("*.py")):
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            names = _import_name_from_node(node)
            for imported in names:
                if imported.startswith("owlclaw.web."):
                    continue
                if imported in {"owlclaw.web", "owlclaw.web.api"}:
                    continue
                if imported.startswith(FORBIDDEN_PREFIXES):
                    violations.append(f"{file_path}: {imported}")

    assert violations == []
