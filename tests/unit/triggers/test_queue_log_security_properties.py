from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.queue import redact_error_message, redact_sensitive_data

_SAFE_VALUE = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_=.:", min_size=4, max_size=48)


@given(
    secret_value=_SAFE_VALUE,
    token_value=_SAFE_VALUE,
    api_key_value=_SAFE_VALUE,
)
@settings(max_examples=40, deadline=None)
def test_property_credentials_are_redacted(secret_value: str, token_value: str, api_key_value: str) -> None:
    """Feature: triggers-queue, Property 23: 凭证安全性."""
    payload = {
        "password": secret_value,
        "token": token_value,
        "api_key": api_key_value,
        "nested": {
            "secret": secret_value,
            "Authorization": f"Bearer {token_value}",
            "meta": f"token={token_value}; password={secret_value}",
        },
    }

    redacted = redact_sensitive_data(payload)
    assert redacted["password"] == "***"
    assert redacted["token"] == "***"
    assert redacted["api_key"] == "***"
    assert redacted["nested"]["secret"] == "***"
    assert redacted["nested"]["Authorization"] == "Bearer ***"
    assert "token=***" in redacted["nested"]["meta"]
    assert "password=***" in redacted["nested"]["meta"]


@given(token_value=_SAFE_VALUE)
@settings(max_examples=40, deadline=None)
def test_property_error_message_is_redacted(token_value: str) -> None:
    """Feature: triggers-queue, Property 23: 错误消息中的凭证会被脱敏."""
    raw = f"request failed: token={token_value}; Authorization=Bearer {token_value}; api_key=sk-{token_value}"

    redacted = redact_error_message(raw)

    assert token_value not in redacted
    assert "Bearer ***" in redacted
    assert "token=***" in redacted
