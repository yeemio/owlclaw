from __future__ import annotations

from pathlib import Path

import pytest

from owlclaw.capabilities.bindings import CredentialResolver


def test_resolve_prefers_os_env_then_env_file_then_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("API_TOKEN=from_env_file\nDB_DSN=from_env_file_dsn\n", encoding="utf-8")
    monkeypatch.setenv("API_TOKEN", "from_os_env")
    resolver = CredentialResolver(env_file=env_file, config_secrets={"DB_DSN": "from_config"})

    assert resolver.resolve("Bearer ${API_TOKEN}") == "Bearer from_os_env"
    assert resolver.resolve("${DB_DSN}") == "from_env_file_dsn"


def test_resolve_uses_config_secrets_fallback(tmp_path: Path) -> None:
    resolver = CredentialResolver(env_file=tmp_path / ".env", config_secrets={"API_KEY": "cfg_value"})
    assert resolver.resolve("token=${API_KEY}") == "token=cfg_value"


def test_resolve_missing_variable_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    resolver = CredentialResolver(env_file=tmp_path / ".env", config_secrets={})
    with pytest.raises(ValueError, match="Missing credential reference"):
        resolver.resolve("${MISSING_SECRET}")


def test_resolve_dict_recursive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN", "abc")
    resolver = CredentialResolver(env_file=tmp_path / ".env")
    payload = {
        "headers": {"Authorization": "Bearer ${TOKEN}"},
        "nested": {"dsn": "postgres://${TOKEN}@host/db"},
        "items": ["${TOKEN}", "plain"],
    }
    resolved = resolver.resolve_dict(payload)
    assert resolved["headers"]["Authorization"] == "Bearer abc"
    assert resolved["nested"]["dsn"] == "postgres://abc@host/db"
    assert resolved["items"][0] == "abc"


def test_contains_potential_secret_heuristics() -> None:
    assert CredentialResolver.contains_potential_secret("Bearer this_is_a_token_123456")
    assert CredentialResolver.contains_potential_secret("api_key=abcdefghijklmno")
    assert not CredentialResolver.contains_potential_secret("${API_KEY}")
    assert not CredentialResolver.contains_potential_secret("safe_value")
