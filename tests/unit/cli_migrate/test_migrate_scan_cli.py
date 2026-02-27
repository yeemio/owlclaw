"""Unit tests for cli-migrate scan command integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.exceptions import Exit
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


def test_migrate_scan_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "paths:\n"
            "  /orders:\n"
            "    post:\n"
            "      operationId: create-order\n"
            "      responses:\n"
            "        '201': {description: created}\n"
        ),
        encoding="utf-8",
    )
    report_json = tmp_path / "custom_report.json"
    report_md = tmp_path / "custom_report.md"

    run_migrate_scan_command(
        openapi=str(spec),
        output_mode="binding",
        output=str(tmp_path),
        report_json=str(report_json),
        report_md=str(report_md),
    )

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["generated_count"] == 1
    assert payload["generated_binding_count"] == 1
    assert report_md.exists()
    assert "Migration Report" in report_md.read_text(encoding="utf-8")


def test_migrate_scan_conflict_exits_without_force(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "paths:\n"
            "  /orders:\n"
            "    post:\n"
            "      operationId: create-order\n"
            "      responses:\n"
            "        '201': {description: created}\n"
        ),
        encoding="utf-8",
    )
    conflict_target = tmp_path / "create-order" / "SKILL.md"
    conflict_target.parent.mkdir(parents=True, exist_ok=True)
    conflict_target.write_text("existing", encoding="utf-8")

    with pytest.raises(Exit) as exc_info:
        run_migrate_scan_command(
            openapi=str(spec),
            output_mode="binding",
            output=str(tmp_path),
        )
    assert exc_info.value.exit_code == 2


def test_migrate_scan_conflict_force_overwrites(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        (
            "openapi: 3.0.3\n"
            "paths:\n"
            "  /orders:\n"
            "    post:\n"
            "      operationId: create-order\n"
            "      responses:\n"
            "        '201': {description: created}\n"
        ),
        encoding="utf-8",
    )
    conflict_target = tmp_path / "create-order" / "SKILL.md"
    conflict_target.parent.mkdir(parents=True, exist_ok=True)
    conflict_target.write_text("existing", encoding="utf-8")

    run_migrate_scan_command(
        openapi=str(spec),
        output_mode="binding",
        output=str(tmp_path),
        force=True,
    )
    assert "existing" not in conflict_target.read_text(encoding="utf-8")


def test_migrate_scan_project_generates_handler_registration_code(tmp_path: Path) -> None:
    project = tmp_path / "legacy_app"
    project.mkdir(parents=True)
    (project / "orders.py").write_text(
        (
            "def calculate_total(price: float, qty: int) -> float:\n"
            "    return price * qty\n"
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    run_migrate_scan_command(project=str(project), output_mode="handler", output=str(out))

    handler_file = out / "handlers" / "calculate-total.py"
    text = handler_file.read_text(encoding="utf-8")
    assert 'def register_handlers(app: Any) -> None:' in text
    assert '@app.handler("calculate-total")' in text
    assert 'module = import_module("orders")' in text


def test_migrate_scan_project_marks_missing_type_hint_for_manual_review(tmp_path: Path) -> None:
    project = tmp_path / "legacy_app"
    project.mkdir(parents=True)
    (project / "orders.py").write_text(
        (
            "def create_order(order_id, qty: int):\n"
            "    return {'id': order_id, 'qty': qty}\n"
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    run_migrate_scan_command(project=str(project), output_mode="handler", output=str(out))

    report = json.loads((out / "migration_report.json").read_text(encoding="utf-8"))
    assert report["stats"]["manual_review_count"] >= 1
    assert any("missing type hint" in item for item in report["manual_review"])


def test_migrate_scan_openapi_mcp_generates_tool_definition_json(tmp_path: Path) -> None:
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
        ),
        encoding="utf-8",
    )

    run_migrate_scan_command(openapi=str(spec), output_mode="mcp", output=str(tmp_path))

    generated = tmp_path / "mcp_tools" / "create-order.json"
    assert generated.exists()
    payload = json.loads(generated.read_text(encoding="utf-8"))
    assert payload["name"] == "create-order"
    assert payload["binding"]["url"] == "https://api.example.com/orders"
    assert payload["binding"]["method"] == "POST"
    assert payload["inputSchema"]["required"] == ["order_id"]

    report_payload = json.loads((tmp_path / "migration_report.json").read_text(encoding="utf-8"))
    assert report_payload["generated_mcp_count"] == 1
    assert report_payload["generated_binding_count"] == 0
    assert report_payload["generated_handler_count"] == 0
