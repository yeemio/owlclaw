"""Runtime mode contract checks for Decision 14 (D14-1)."""

from __future__ import annotations

from pathlib import Path

from owlclaw import OwlClaw


def test_start_docstring_declares_external_heartbeat_responsibility() -> None:
    doc = OwlClaw.start.__doc__ or ""
    normalized = doc.lower()
    assert "does not create a background heartbeat loop" in normalized
    assert "runtime.trigger_event" in doc


def test_run_docstring_declares_builtin_heartbeat_loop() -> None:
    doc = OwlClaw.run.__doc__ or ""
    normalized = doc.lower()
    assert "internal heartbeat loop" in normalized
    assert "unlike `start()`" in normalized


def test_quick_start_documents_embedded_mode_heartbeat() -> None:
    payload = Path("docs/QUICK_START.md").read_text(encoding="utf-8")
    assert "服务化嵌入模式（`app.start()`）" in payload
    assert 'runtime.trigger_event("heartbeat"' in payload


def test_complete_workflow_readme_documents_embedded_mode_heartbeat() -> None:
    payload = Path("examples/complete_workflow/README.md").read_text(encoding="utf-8")
    assert "服务化模式 heartbeat 配置（`app.start()`）" in payload
    assert 'runtime.trigger_event("heartbeat"' in payload
