"""Unit tests for DataMasker."""

from owlclaw.security.audit import SecurityAuditLog
from owlclaw.security.data_masker import DataMasker


def test_data_masker_masks_text_patterns() -> None:
    masker = DataMasker()
    text = "email: user@example.com token=abc123"
    masked = masker.mask(text)
    assert "[REDACTED]" in masked
    assert "user@example.com" not in masked


def test_data_masker_masks_nested_dict_fields() -> None:
    masker = DataMasker()
    payload = {
        "phone": "+1 212-555-0011",
        "profile": {
            "email": "person@example.com",
            "api_key": "secret-token",
        },
        "history": [
            {"bank_card": "6222021234567890"},
            {"note": "normal text"},
        ],
    }
    masked = masker.mask(payload)
    assert masked["phone"] != payload["phone"]
    assert masked["profile"]["email"] != payload["profile"]["email"]
    assert masked["profile"]["api_key"] == "[REDACTED]"
    assert masked["history"][0]["bank_card"] != payload["history"][0]["bank_card"]


def test_data_masker_writes_audit_event_when_mask_applied() -> None:
    audit = SecurityAuditLog()
    masker = DataMasker(audit_log=audit)
    masked = masker.mask("email: user@example.com")
    assert "[REDACTED]" in masked
    event_types = [e.event_type for e in audit.list_events()]
    assert "mask_applied" in event_types
