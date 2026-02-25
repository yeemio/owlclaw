"""Unit tests for cli-migrate binding generator (OpenAPI/ORM)."""

from __future__ import annotations

from typer.testing import CliRunner

from owlclaw.cli.migrate.generators import (
    BindingGenerator,
    OpenAPIEndpoint,
    ORMOperation,
)
from owlclaw.cli.skill import skill_app

runner = CliRunner()


def test_generate_from_openapi_builds_http_binding_and_prerequisites() -> None:
    generator = BindingGenerator()
    endpoint = OpenAPIEndpoint(
        method="get",
        path="/orders/{order_id}",
        operation_id="getOrderById",
        summary="Get order by id",
        description="Fetch order detail from upstream service",
        parameters=[
            {"name": "order_id", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "include_items", "in": "query", "required": False, "schema": {"type": "boolean"}},
        ],
        responses={
            "200": {
                "description": "ok",
                "content": {"application/json": {"schema": {"type": "object", "properties": {"data": {"type": "object"}}}}},
            },
            "404": {"description": "not found"},
            "429": {"description": "too many requests"},
        },
        security=[{"BearerAuth": []}],
        security_schemes={"BearerAuth": {"type": "http", "scheme": "bearer"}},
        server_url="https://api.example.com",
    )

    result = generator.generate_from_openapi(endpoint)

    assert result.binding_type == "http"
    assert result.skill_name == "getorderbyid"
    assert result.tools_count == 1
    assert result.prerequisites_env == ["BEARERAUTH_TOKEN"]
    assert "Authorization: Bearer ${BEARERAUTH_TOKEN}" in result.skill_content
    assert "url: https://api.example.com/orders/{order_id}" in result.skill_content
    assert "order_id" in result.skill_content
    assert "include_items" in result.skill_content
    assert "path: $.data" in result.skill_content


def test_generate_from_openapi_output_passes_skill_validate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XAPI_API_KEY", "token")
    generator = BindingGenerator()
    endpoint = OpenAPIEndpoint(
        method="post",
        path="/orders",
        operation_id="create-order",
        description="create order",
        request_body={
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
                        "required": ["order_id"],
                    }
                }
            }
        },
        responses={"201": {"description": "created"}},
        security=[{"xApi": []}],
        security_schemes={"xApi": {"type": "apiKey", "in": "header", "name": "X-API-Key"}},
        server_url="https://billing.example.com",
    )
    content = generator.generate_from_openapi(endpoint).skill_content
    skill_dir = tmp_path / "generated-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    result = runner.invoke(skill_app, ["validate", str(skill_dir)])
    assert result.exit_code == 0
    assert "OK:" in result.output


def test_generate_from_orm_enforces_parameterized_read_only_query() -> None:
    generator = BindingGenerator()
    result = generator.generate_from_orm(
        ORMOperation(
            model_name="InventoryItem",
            table_name="inventory_items",
            columns=["sku", "qty"],
            filters=["sku"],
            connection_env="READ_DB_DSN",
        )
    )
    assert result.binding_type == "sql"
    assert "type: sql" in result.skill_content
    assert "read_only: true" in result.skill_content
    assert "query: SELECT sku, qty FROM inventory_items WHERE sku = :sku" in result.skill_content
    assert "connection: ${READ_DB_DSN}" in result.skill_content
