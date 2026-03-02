"""Tests for OwlClaw app console mount integration."""

from __future__ import annotations

from owlclaw.app import OwlClaw


def test_create_http_app_calls_console_mount(monkeypatch) -> None:
    app = OwlClaw("demo")
    captured: dict[str, bool] = {}

    def _fake_mount_console(host):  # type: ignore[no-untyped-def]
        _ = host
        captured["called"] = True
        return True

    monkeypatch.setattr("owlclaw.app.mount_console", _fake_mount_console)
    http_app = app.create_http_app()

    assert captured["called"] is True
    assert http_app is not None

