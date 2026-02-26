"""Unit tests for owlclaw CLI main entrypoint dispatch behavior."""

from __future__ import annotations

import contextlib
import importlib

import pytest
from click.exceptions import Exit


def test_main_dispatches_skill_templates_with_option_value(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    captured: dict[str, object] = {}

    def _fake_templates_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.skill_list.templates_command", _fake_templates_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "templates", "--category", "MONITORING"])
    cli_main.main()

    assert captured["category"] == "MONITORING"
    assert captured["search"] == ""
    assert captured["json_output"] is False


def test_main_version_flag_prints_version(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "owlclaw " in out


def test_main_short_version_flag_prints_version(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "-V"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "owlclaw " in out


def test_main_root_help_includes_version_option(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--version, -V" in out


def test_main_dispatches_skill_init_with_template_value(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    captured: dict[str, object] = {}

    def _fake_init_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        raise Exit(0)

    monkeypatch.setattr("owlclaw.cli.skill_init.init_command", _fake_init_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "skill",
            "init",
            "--template",
            "monitoring/health-check",
            "--output",
            str(tmp_path),
        ],
    )
    with contextlib.suppress(SystemExit):
        cli_main.main()

    assert captured["template"] == "monitoring/health-check"
    assert captured["path"] == str(tmp_path)


def test_main_dispatches_skill_init_with_from_binding(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_init_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        raise Exit(0)

    monkeypatch.setattr("owlclaw.cli.skill_init.init_command", _fake_init_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "skill",
            "init",
            "--name",
            "biz-rules",
            "--from-binding",
            str(tmp_path / "src" / "SKILL.md"),
            "--output",
            str(tmp_path),
        ],
    )
    with contextlib.suppress(SystemExit):
        cli_main.main()

    assert captured["name"] == "biz-rules"
    assert captured["from_binding"] == str(tmp_path / "src" / "SKILL.md")


def test_main_converts_click_exit_to_system_exit(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    def _fake_templates_command(**kwargs):  # type: ignore[no-untyped-def]
        raise Exit(2)

    monkeypatch.setattr("owlclaw.cli.skill_list.templates_command", _fake_templates_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "templates"])

    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 2


def test_main_skill_templates_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "templates", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill templates [OPTIONS]" in out


def test_main_skill_init_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "init", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill init [OPTIONS]" in out


def test_main_skill_create_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "create", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill create [OPTIONS]" in out


def test_main_skill_without_subcommand_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill [OPTIONS] COMMAND [ARGS]..." in out
    assert "search" in out
    assert "Examples:" in out


def test_main_skill_search_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "search", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill search [OPTIONS]" in out
    assert "--quiet" in out


def test_main_dispatches_skill_create(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_create_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.skill_create.create_command", _fake_create_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "create", "--interactive", "--output", "skills"])
    cli_main.main()
    assert captured["interactive"] is True
    assert captured["output"] == "skills"


def test_main_skill_create_from_template_generates_file(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "skill",
            "create",
            "--from-template",
            "inventory-monitor",
            "--output",
            str(tmp_path),
        ],
    )
    cli_main.main()
    generated = tmp_path / "inventory-monitor" / "SKILL.md"
    assert generated.exists()


def test_main_skill_ai_assist_end_to_end_create_validate_parse(monkeypatch, tmp_path, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")

    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "skill",
            "create",
            "--from-template",
            "inventory-monitor",
            "--output",
            str(tmp_path),
        ],
    )
    cli_main.main()

    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "validate", str(tmp_path)])
    cli_main.main()
    validate_out = capsys.readouterr().out
    assert "Validated" in validate_out

    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "parse", str(tmp_path)])
    cli_main.main()
    parse_out = capsys.readouterr().out
    assert '"name": "inventory-monitor"' in parse_out


def test_main_dispatches_skill_parse(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_parse_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.skill_parse.parse_command", _fake_parse_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "parse", str(tmp_path), "--cache"])
    cli_main.main()
    assert captured["path"] == str(tmp_path)
    assert captured["cache"] is True


def test_main_skill_parse_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "parse", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw skill parse [PATH] [--cache]" in out


def test_main_dispatches_skill_install_verbose_and_quiet(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_install_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.skill_hub.install_command", _fake_install_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "install", "demo", "--verbose", "--quiet"])
    cli_main.main()
    assert captured["name"] == "demo"
    assert captured["verbose"] is True
    assert captured["quiet"] is True


def test_main_skill_unknown_subcommand_exits_2(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "skill", "unknown-sub"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "unknown skill subcommand" in err.lower()


def test_main_dispatches_db_rollback(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_rollback_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.db_rollback.rollback_command", _fake_rollback_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "db",
            "rollback",
            "--target",
            "base",
            "--database-url",
            "postgresql://u:p@localhost/owlclaw",
            "--dry-run",
            "--yes",
        ],
    )
    cli_main.main()
    assert captured["target"] == "base"
    assert captured["steps"] == 0
    assert captured["dry_run"] is True
    assert captured["yes"] is True


def test_main_db_rollback_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "db", "rollback", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    assert "Usage: owlclaw db rollback [OPTIONS]" in capsys.readouterr().out


def test_main_dispatches_migrate_scan_with_output_mode(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_run_migrate_scan_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migrate.scan_cli.run_migrate_scan_command", _fake_run_migrate_scan_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "migrate",
            "scan",
            "--project",
            str(tmp_path / "legacy"),
            "--openapi",
            str(tmp_path / "openapi.yaml"),
            "--output-mode",
            "binding",
            "--output",
            str(tmp_path / "out"),
            "--dry-run",
            "--report-json",
            str(tmp_path / "r.json"),
            "--report-md",
            str(tmp_path / "r.md"),
            "--force",
        ],
    )
    cli_main.main()
    assert captured["output_mode"] == "binding"
    assert captured["project"] == str(tmp_path / "legacy")
    assert captured["openapi"] == str(tmp_path / "openapi.yaml")
    assert captured["output"] == str(tmp_path / "out")
    assert captured["dry_run"] is True
    assert captured["report_json"] == str(tmp_path / "r.json")
    assert captured["report_md"] == str(tmp_path / "r.md")
    assert captured["force"] is True


def test_main_migrate_scan_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "migrate", "scan", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw migrate scan [OPTIONS]" in out
    assert "--project" in out
    assert "--output-mode [handler|binding|both]" in out
    assert "--dry-run" in out
    assert "--report-json" in out
    assert "--report-md" in out
    assert "--force" in out


def test_main_dispatches_migrate_init(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_init_migrate_config_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr(
        "owlclaw.cli.migrate.config_cli.init_migrate_config_command",
        _fake_init_migrate_config_command,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "migrate",
            "init",
            "--path",
            str(tmp_path),
            "--project",
            "./legacy",
            "--output",
            "./out",
            "--output-mode",
            "binding",
            "--non-interactive",
        ],
    )
    cli_main.main()
    assert captured["path"] == str(tmp_path)
    assert captured["project"] == "./legacy"
    assert captured["output_mode"] == "binding"
    assert captured["interactive"] is False


def test_main_dispatches_migrate_config_validate(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_validate_migrate_config_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr(
        "owlclaw.cli.migrate.config_cli.validate_migrate_config_command",
        _fake_validate_migrate_config_command,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "migrate",
            "config",
            "validate",
            "--config",
            str(tmp_path / ".owlclaw-migrate.yaml"),
        ],
    )
    cli_main.main()
    assert captured["config"] == str(tmp_path / ".owlclaw-migrate.yaml")


def test_main_release_gate_owlhub_help_uses_plain_help(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "release", "gate", "owlhub", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Usage: owlclaw release gate owlhub [OPTIONS]" in out


def test_main_dispatches_release_gate_owlhub(monkeypatch, tmp_path) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_release_gate_owlhub_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.release_gate.release_gate_owlhub_command", _fake_release_gate_owlhub_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owlclaw",
            "release",
            "gate",
            "owlhub",
            "--api-base-url",
            "http://127.0.0.1:18080",
            "--index-url",
            "file:///tmp/index.json",
            "--query",
            "local",
            "--work-dir",
            str(tmp_path),
            "--output",
            str(tmp_path / "gate.json"),
        ],
    )
    cli_main.main()
    assert captured["api_base_url"] == "http://127.0.0.1:18080"
    assert captured["index_url"] == "file:///tmp/index.json"
    assert captured["query"] == "local"
    assert captured["work_dir"] == str(tmp_path)
    assert captured["output"] == str(tmp_path / "gate.json")


def test_main_prints_version(monkeypatch, capsys) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    monkeypatch.setattr("sys.argv", ["owlclaw", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("owlclaw ")


def test_main_dispatches_migration_status(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_status_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migration.status_command", _fake_status_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "migration", "status", "--config", "owlclaw.yaml"])
    cli_main.main()
    assert captured["config"] == "owlclaw.yaml"


def test_main_dispatches_migration_set(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_set_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migration.set_command", _fake_set_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "migration", "set", "inventory-check", "70"])
    cli_main.main()
    assert captured["skill"] == "inventory-check"
    assert captured["weight"] == 70


def test_main_dispatches_migration_suggest(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_suggest_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migration.suggest_command", _fake_suggest_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "migration", "suggest"])
    cli_main.main()
    assert captured["config"] == ""


def test_main_dispatches_approval_list(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_approval_list_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migration.approval_list_command", _fake_approval_list_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "approval", "list", "--status", "pending"])
    cli_main.main()
    assert captured["status"] == "pending"


def test_main_dispatches_approval_approve(monkeypatch) -> None:
    cli_main = importlib.import_module("owlclaw.cli.__init__")
    captured: dict[str, object] = {}

    def _fake_approval_approve_command(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)

    monkeypatch.setattr("owlclaw.cli.migration.approval_approve_command", _fake_approval_approve_command)
    monkeypatch.setattr("sys.argv", ["owlclaw", "approval", "approve", "req-1", "--approver", "ops-a"])
    cli_main.main()
    assert captured["request_id"] == "req-1"
    assert captured["approver"] == "ops-a"
