"""CLI handlers for `owlclaw migrate scan`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import typer
import yaml  # type: ignore[import-untyped]

from owlclaw.cli.migrate.generators import BindingGenerator, OpenAPIEndpoint, ORMOperation

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def run_migrate_scan_command(
    *,
    openapi: str = "",
    orm: str = "",
    output_mode: str = "handler",
    output: str = ".",
    dry_run: bool = False,
) -> None:
    mode = output_mode.strip().lower()
    if mode not in {"handler", "binding", "both"}:
        raise typer.Exit(2)
    if not openapi.strip() and not orm.strip():
        raise typer.Exit(2)

    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    generator = BindingGenerator()

    endpoint_results: list[str] = []
    orm_results: list[str] = []

    if openapi.strip():
        endpoints = _load_openapi_endpoints(Path(openapi))
        for endpoint in endpoints:
            result = generator.generate_from_openapi(endpoint)
            if mode in {"binding", "both"}:
                target = output_dir / result.skill_name / "SKILL.md"
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(result.skill_content, encoding="utf-8")
                endpoint_results.append(str(target))
            if mode in {"handler", "both"}:
                if dry_run:
                    endpoint_results.append(str(output_dir / "handlers" / f"{result.skill_name}.py"))
                else:
                    endpoint_results.append(str(_write_handler_stub(output_dir, result.skill_name)))

    if orm.strip():
        operations = _load_orm_operations(Path(orm))
        for operation in operations:
            result = generator.generate_from_orm(operation)
            if mode in {"binding", "both"}:
                target = output_dir / result.skill_name / "SKILL.md"
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(result.skill_content, encoding="utf-8")
                orm_results.append(str(target))
            if mode in {"handler", "both"}:
                if dry_run:
                    orm_results.append(str(output_dir / "handlers" / f"{result.skill_name}.py"))
                else:
                    orm_results.append(str(_write_handler_stub(output_dir, result.skill_name)))

    generated = endpoint_results + orm_results
    if not generated:
        raise typer.Exit(2)
    typer.echo(f"generated={len(generated)}")
    if dry_run:
        typer.echo("dry_run=true")
    for path in generated:
        typer.echo(path)


def _load_openapi_endpoints(path: Path) -> list[OpenAPIEndpoint]:
    payload = _load_data(path)
    if not isinstance(payload, dict):
        return []

    servers = payload.get("servers", [])
    server_url = ""
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            server_url = str(first.get("url", "")).strip()

    components = payload.get("components", {})
    security_schemes: dict[str, dict[str, Any]] = {}
    if isinstance(components, dict):
        raw = components.get("securitySchemes", {})
        if isinstance(raw, dict):
            for name, spec in raw.items():
                if isinstance(name, str) and isinstance(spec, dict):
                    security_schemes[name] = spec

    global_security = payload.get("security", [])
    endpoints: list[OpenAPIEndpoint] = []
    paths = payload.get("paths", {})
    if not isinstance(paths, dict):
        return []
    for api_path, operations in paths.items():
        if not isinstance(api_path, str) or not isinstance(operations, dict):
            continue
        for method, op in operations.items():
            m = str(method).lower()
            if m not in _HTTP_METHODS or not isinstance(op, dict):
                continue
            security = op.get("security", global_security)
            endpoints.append(
                OpenAPIEndpoint(
                    method=m,
                    path=api_path,
                    operation_id=str(op.get("operationId", "")),
                    summary=str(op.get("summary", "")),
                    description=str(op.get("description", "")),
                    parameters=op.get("parameters", []) if isinstance(op.get("parameters", []), list) else [],
                    request_body=op.get("requestBody", {}) if isinstance(op.get("requestBody", {}), dict) else {},
                    responses=op.get("responses", {}) if isinstance(op.get("responses", {}), dict) else {},
                    security=security if isinstance(security, list) else [],
                    security_schemes=security_schemes,
                    server_url=server_url,
                )
            )
    return endpoints


def _load_orm_operations(path: Path) -> list[ORMOperation]:
    payload = _load_data(path)
    if not isinstance(payload, dict):
        return []
    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        return []
    out: list[ORMOperation] = []
    for item in operations:
        if not isinstance(item, dict):
            continue
        model_name = str(item.get("model_name", "")).strip()
        table_name = str(item.get("table_name", "")).strip()
        if not model_name or not table_name:
            continue
        columns = item.get("columns", [])
        filters = item.get("filters", [])
        out.append(
            ORMOperation(
                model_name=model_name,
                table_name=table_name,
                columns=[str(c) for c in columns if isinstance(c, str)],
                filters=[str(c) for c in filters if isinstance(c, str)],
                connection_env=str(item.get("connection_env", "READ_DB_DSN")),
            )
        )
    return out


def _load_data(path: Path) -> dict[str, Any] | list[Any] | str | None:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return cast(dict[str, Any] | list[Any] | str | None, json.loads(text))
    return cast(dict[str, Any] | list[Any] | str | None, yaml.safe_load(text))


def _write_handler_stub(output_dir: Path, skill_name: str) -> Path:
    handlers_dir = output_dir / "handlers"
    handlers_dir.mkdir(parents=True, exist_ok=True)
    path = handlers_dir / f"{skill_name}.py"
    path.write_text(
        (
            "from __future__ import annotations\n\n"
            f"async def {skill_name.replace('-', '_')}_handler(params: dict) -> dict:\n"
            '    """Generated handler stub from migrate scan."""\n'
            '    return {"status": "todo", "params": params}\n'
        ),
        encoding="utf-8",
    )
    return path
