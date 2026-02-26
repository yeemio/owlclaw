"""Consistency checks for docs/protocol/ERROR_MODEL.md mapping matrix."""

from __future__ import annotations

from pathlib import Path


def test_error_model_mapping_matrix_contains_required_columns_and_rows() -> None:
    payload = Path("docs/protocol/ERROR_MODEL.md").read_text(encoding="utf-8")
    assert "| Canonical code | API status | MCP surface | Category | Retryable | Alert level |" in payload
    required_codes = [
        "protocol.unsupported_version",
        "governance.rate_limited",
        "governance.budget_exceeded",
        "runtime.timeout",
        "internal.unexpected",
    ]
    for code in required_codes:
        assert f"| `{code}` |" in payload


def test_error_model_requires_machine_readable_core_fields() -> None:
    payload = Path("docs/protocol/ERROR_MODEL.md").read_text(encoding="utf-8")
    required_fields = ["`code`", "`category`", "`retryable`", "`incident_id`"]
    for field in required_fields:
        assert field in payload
