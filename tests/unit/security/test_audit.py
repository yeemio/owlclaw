"""Unit tests for SecurityAuditLog."""

import json
from pathlib import Path

from owlclaw.security.audit import FileSecurityAuditBackend, SecurityAuditLog


def test_security_audit_log_records_and_lists_events() -> None:
    audit = SecurityAuditLog()
    event = audit.record(
        event_type="sanitization",
        source="webhook",
        details={"changed": True, "rule": "ignore previous"},
    )
    events = audit.list_events()
    assert len(events) == 1
    assert events[0] == event
    assert events[0].event_type == "sanitization"
    assert events[0].source == "webhook"


def test_security_audit_log_persists_to_file_backend(tmp_path: Path) -> None:
    log_file = tmp_path / "security-audit.jsonl"
    audit = SecurityAuditLog(backend=FileSecurityAuditBackend(log_file))
    audit.record(event_type="tool_result_sanitized", source="runtime", details={"tool": "scan"})
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event_type"] == "tool_result_sanitized"
    assert payload["source"] == "runtime"


def test_security_audit_log_uses_env_file_backend(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "audit.log"
    monkeypatch.setenv("OWLCLAW_SECURITY_AUDIT_BACKEND", "file")
    monkeypatch.setenv("OWLCLAW_SECURITY_AUDIT_FILE", str(log_file))
    audit = SecurityAuditLog()
    audit.record(event_type="sanitization", source="api", details={"changed": True})
    assert log_file.exists()
