"""Property tests for cli-db configuration and validation behavior."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import HealthCheck
from hypothesis import settings
from hypothesis import strategies as st

from owlclaw.cli.db_backup import backup_command
from owlclaw.cli.db_check import check_command
from owlclaw.cli.db_restore import restore_command
from owlclaw.cli.db_rollback import rollback_command


def _url_for(db_name: str) -> str:
    safe_name = "".join(ch for ch in db_name if ch.isalnum() or ch in ("_", "-")) or "db"
    return f"postgresql://u:p@localhost/{safe_name}"


@given(
    env_name=st.text(min_size=1, max_size=12),
    explicit_name=st.text(min_size=1, max_size=12),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_config_priority_explicit_url_over_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    env_name: str,
    explicit_name: str,
) -> None:
    """Property: explicit --database-url has higher priority than environment URL."""
    env_url = _url_for(env_name)
    explicit_url = _url_for(explicit_name)
    output = tmp_path / "backup.sql"
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", env_url)
    monkeypatch.setattr("owlclaw.cli.db_backup._check_pg_dump_available", lambda: True)
    monkeypatch.setattr("owlclaw.cli.db_backup.progress_after", lambda *_a, **_k: nullcontext())
    monkeypatch.setattr("builtins.input", lambda _p: "y")
    captured: dict[str, str] = {}

    def _fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        captured["conn"] = args[args.index("-d") + 1]
        output_path = Path(args[args.index("-f") + 1])
        output_path.write_text("-- dump", encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("owlclaw.cli.db_backup.subprocess.run", _fake_run)
    backup_command(
        output=str(output),
        format_name="plain",
        schema_only=False,
        data_only=False,
        database_url=explicit_url,
        verbose=False,
    )
    assert captured["conn"] == explicit_url


@given(st.sampled_from(["backup_missing_url", "restore_missing_url", "check_missing_url"]))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_exit_code_for_missing_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scenario: str
) -> None:
    """Property: commands requiring DB URL exit with code 2 when URL is missing."""
    monkeypatch.delenv("OWLCLAW_DATABASE_URL", raising=False)
    if scenario == "backup_missing_url":
        with pytest.raises(Exception) as exc_info:
            backup_command(
                output=str(tmp_path / "a.sql"),
                format_name="plain",
                schema_only=False,
                data_only=False,
                database_url="",
                verbose=False,
            )
    elif scenario == "restore_missing_url":
        f = tmp_path / "x.sql"
        f.write_text("select 1;", encoding="utf-8")
        with pytest.raises(Exception) as exc_info:
            restore_command(input_path=str(f), clean=False, database_url="", yes=True, verbose=False)
    else:
        with pytest.raises(Exception) as exc_info:
            check_command(database_url="", verbose=False)
    assert getattr(exc_info.value, "exit_code", None) == 2


@given(st.sampled_from(["backup_mutual_exclusive", "backup_bad_format", "rollback_conflict", "restore_missing_input"]))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_parameter_validation_consistency(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scenario: str) -> None:
    """Property: invalid parameter combinations fail fast with exit code 2."""
    monkeypatch.setenv("OWLCLAW_DATABASE_URL", "postgresql://u:p@localhost/owlclaw")
    if scenario == "backup_mutual_exclusive":
        with pytest.raises(Exception) as exc_info:
            backup_command(
                output=str(tmp_path / "a.sql"),
                format_name="plain",
                schema_only=True,
                data_only=True,
                database_url="",
                verbose=False,
            )
    elif scenario == "backup_bad_format":
        with pytest.raises(Exception) as exc_info:
            backup_command(
                output=str(tmp_path / "a.sql"),
                format_name="zip",
                schema_only=False,
                data_only=False,
                database_url="",
                verbose=False,
            )
    elif scenario == "rollback_conflict":
        with pytest.raises(Exception) as exc_info:
            rollback_command(target="abc123", steps=1, database_url="", dry_run=True, yes=True)
    else:
        with pytest.raises(Exception) as exc_info:
            restore_command(input_path="", clean=False, database_url="", yes=True, verbose=False)
    assert getattr(exc_info.value, "exit_code", None) == 2
