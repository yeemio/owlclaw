"""Keep examples index README aligned with actual repository paths."""

from __future__ import annotations

import re
from pathlib import Path


def test_examples_readme_referenced_paths_exist() -> None:
    repo = Path(__file__).resolve().parents[2]
    lines = (repo / "examples" / "README.md").read_text(encoding="utf-8").splitlines()
    # Only parse markdown table rows to avoid matching fenced code blocks.
    table = [line for line in lines if line.startswith("| `")]
    referenced: list[str] = []
    for line in table:
        match = re.search(r"`([^`]+)`", line)
        if match:
            referenced.append(match.group(1))
    assert referenced, "examples/README.md should reference at least one example path"
    for rel in referenced:
        candidate = repo / "examples" / rel
        assert candidate.exists(), f"examples index references missing path: {rel}"
