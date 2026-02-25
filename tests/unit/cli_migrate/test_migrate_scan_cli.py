"""Unit tests for cli-migrate scan command integration."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.cli.migrate.scan_cli import run_migrate_scan_command
from owlclaw.cli.skill import skill_app

runner = CliRunner()


def test_migrate_scan_openapi_binding_generates_valid_skill_and_loadable_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XAPI_API_KEY", "token")
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "servers:\n"
            "  - url: https://api.example.com\n"
            "paths:\n"
            "  /orders:\n"
            "    post:\n"
            "      operationId: create-order\n"
            "      description: create order\n"
            "      requestBody:\n"
            "        content:\n"
            "          application/json:\n"
            "            schema:\n"
            "              type: object\n"
            "              properties:\n"
            "                order_id: {type: string}\n"
            "              required: [order_id]\n"
            "      responses:\n"
            "        '201': {description: created}\n"
            "      security:\n"
            "        - xApi: []\n"
            "components:\n"
            "  securitySchemes:\n"
            "    xApi:\n"
            "      type: apiKey\n"
            "      in: header\n"
            "      name: X-API-Key\n"
        ),
        encoding="utf-8",
    )

    run_migrate_scan_command(openapi=str(spec), output_mode="binding", output=str(tmp_path))

    skill_dir = tmp_path / "create-order"
    result = runner.invoke(skill_app, ["validate", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK:" in result.output

    skills = SkillsLoader(tmp_path).scan()
    assert any(skill.name == "create-order" for skill in skills)


def test_migrate_scan_orm_binding_generates_valid_skill_and_loadable_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("READ_DB_DSN", "postgresql+psycopg://u:p@localhost:5432/app")
    orm_spec = tmp_path / "orm.yaml"
    orm_spec.write_text(
        (
            "operations:\n"
            "  - model_name: Order\n"
            "    table_name: orders\n"
            "    columns: [id, status]\n"
            "    filters: [id]\n"
            "    connection_env: READ_DB_DSN\n"
        ),
        encoding="utf-8",
    )

    run_migrate_scan_command(orm=str(orm_spec), output_mode="binding", output=str(tmp_path))

    skill_dir = tmp_path / "order-query"
    result = runner.invoke(skill_app, ["validate", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK:" in result.output

    skills = SkillsLoader(tmp_path).scan()
    assert any(skill.name == "order-query" for skill in skills)


def test_migrate_scan_both_generates_handler_and_binding(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "paths:\n"
            "  /orders/{id}:\n"
            "    get:\n"
            "      operationId: get-order\n"
            "      responses:\n"
            "        '200': {description: ok}\n"
        ),
        encoding="utf-8",
    )

    run_migrate_scan_command(openapi=str(spec), output_mode="both", output=str(tmp_path))

    assert (tmp_path / "get-order" / "SKILL.md").exists()
    assert (tmp_path / "handlers" / "get-order.py").exists()


def test_migrate_scan_dry_run_does_not_write_files(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "paths:\n"
            "  /orders/{id}:\n"
            "    get:\n"
            "      operationId: get-order\n"
            "      responses:\n"
            "        '200': {description: ok}\n"
        ),
        encoding="utf-8",
    )

    run_migrate_scan_command(
        openapi=str(spec),
        output_mode="both",
        output=str(tmp_path),
        dry_run=True,
    )

    assert not (tmp_path / "get-order" / "SKILL.md").exists()
    assert not (tmp_path / "handlers" / "get-order.py").exists()
