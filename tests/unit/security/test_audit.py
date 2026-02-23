"""Unit tests for SecurityAuditLog."""

from owlclaw.security.audit import SecurityAuditLog


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
