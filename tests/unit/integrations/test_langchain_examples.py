"""Validate LangChain example scripts are present and syntactically valid."""

from __future__ import annotations

import ast
from pathlib import Path


def test_langchain_examples_exist_and_parse() -> None:
    base = Path("examples/langchain")
    files = sorted(path for path in base.glob("*.py"))

    assert len(files) >= 5

    for file_path in files:
        source = file_path.read_text(encoding="utf-8")
        ast.parse(source)
