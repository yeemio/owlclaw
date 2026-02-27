"""Checks for API/MCP alignment matrix baseline."""

from __future__ import annotations

from pathlib import Path


def test_api_mcp_alignment_matrix_exists_with_required_sections() -> None:
    payload = Path("docs/protocol/API_MCP_ALIGNMENT_MATRIX.md").read_text(encoding="utf-8")
    assert "## 1. Capability Alignment" in payload
    assert "## 2. Error-domain Alignment" in payload
    assert "## 3. Review Requirement" in payload
    assert "protocol.unsupported_version" in payload
