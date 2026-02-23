"""Unit tests for owlclaw db health check command."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from owlclaw.cli.db_check import _check_connection_pool, check_command


class _FakeEngine:
    def __init__(self, size: int = 10, checked_out: int = 0) -> None:
        pool = SimpleNamespace(size=lambda: size, checkedout=lambda: checked_out)
        self.sync_engine = SimpleNamespace(pool=pool, dispose=lambda: None)


def test_check_command_all_ok(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_check.get_engine", lambda _u: _FakeEngine())
    async def _fake_run_checks(_e, verbose=False):  # type: ignore[no-untyped-def]
        return [
            {"name": "Connection", "status": "OK", "message": "ok"},
            {"name": "Migration", "status": "OK", "message": "ok"},
        ]

    monkeypatch.setattr("owlclaw.cli.db_check._run_health_checks", _fake_run_checks)
    monkeypatch.setattr("owlclaw.cli.db_check._print_health_report", lambda *_a, **_k: None)
    check_command(database_url="", verbose=False)


def test_check_command_with_warning_still_ok(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_check.get_engine", lambda _u: _FakeEngine())
    async def _fake_run_checks(_e, verbose=False):  # type: ignore[no-untyped-def]
        return [
            {"name": "Connection", "status": "OK", "message": "ok"},
            {"name": "Migration", "status": "WARN", "message": "pending"},
        ]

    monkeypatch.setattr("owlclaw.cli.db_check._run_health_checks", _fake_run_checks)
    monkeypatch.setattr("owlclaw.cli.db_check._print_health_report", lambda *_a, **_k: None)
    check_command(database_url="", verbose=False)


def test_check_command_with_error_exits_1(monkeypatch) -> None:
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    monkeypatch.setattr("owlclaw.cli.db_check.get_engine", lambda _u: _FakeEngine())
    async def _fake_run_checks(_e, verbose=False):  # type: ignore[no-untyped-def]
        return [
            {"name": "Connection", "status": "ERROR", "message": "failed"},
        ]

    monkeypatch.setattr("owlclaw.cli.db_check._run_health_checks", _fake_run_checks)
    monkeypatch.setattr("owlclaw.cli.db_check._print_health_report", lambda *_a, **_k: None)
    with pytest.raises(Exception) as exc_info:
        check_command(database_url="", verbose=False)
    assert getattr(exc_info.value, "exit_code", None) == 1


@pytest.mark.asyncio
async def test_check_connection_pool_thresholds() -> None:
    ok_result = await _check_connection_pool(_FakeEngine(size=10, checked_out=2))
    warn_result = await _check_connection_pool(_FakeEngine(size=10, checked_out=8))
    error_result = await _check_connection_pool(_FakeEngine(size=10, checked_out=10))
    assert ok_result["status"] == "OK"
    assert warn_result["status"] == "WARN"
    assert error_result["status"] == "ERROR"
