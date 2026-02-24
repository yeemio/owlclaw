"""Webhook payload parsing and transformation service."""

from __future__ import annotations

import ast
import json
from datetime import datetime
from urllib.parse import parse_qs
from xml.etree import ElementTree

from owlclaw.triggers.webhook.types import (
    AgentInput,
    HttpRequest,
    ParsedPayload,
    TransformationRule,
    ValidationError,
    ValidationResult,
)


class PayloadTransformer:
    """Parse incoming payloads and map them to AgentInput."""

    def parse(self, request: HttpRequest) -> ParsedPayload:
        content_type = _extract_content_type(request.headers)
        body = request.body
        if content_type == "application/json":
            try:
                data = json.loads(body) if body else {}
                if not isinstance(data, dict):
                    raise ValueError("json payload must be an object")
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError("invalid json payload") from exc
            return ParsedPayload(content_type=content_type, data=data, headers=request.headers, raw_body=body)
        if content_type in {"application/xml", "text/xml"}:
            try:
                root = ElementTree.fromstring(body)
                data = {_strip_ns(root.tag): _xml_to_dict(root)}
            except ElementTree.ParseError as exc:
                raise ValueError("invalid xml payload") from exc
            return ParsedPayload(content_type=content_type, data=data, headers=request.headers, raw_body=body)
        if content_type == "application/x-www-form-urlencoded":
            parsed = parse_qs(body, keep_blank_values=True)
            data = {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}
            return ParsedPayload(content_type=content_type, data=data, headers=request.headers, raw_body=body)
        raise ValueError("unsupported content type")

    def parse_safe(self, request: HttpRequest) -> tuple[ParsedPayload | None, ValidationResult]:
        try:
            return self.parse(request), ValidationResult(valid=True)
        except ValueError as exc:
            return None, ValidationResult(
                valid=False,
                error=ValidationError(
                    code="INVALID_FORMAT",
                    message=str(exc),
                    status_code=400,
                ),
            )

    def transform(self, payload: ParsedPayload, rule: TransformationRule) -> AgentInput:
        parameters: dict[str, object] = {}
        for mapping in rule.mappings:
            raw_value = _json_path_get(payload.data, mapping.source)
            value = mapping.default if raw_value is None else raw_value
            converted = _convert_value(value, mapping.transform)
            _assign_path(parameters, mapping.target, converted)
        if rule.custom_logic:
            logic_result = _evaluate_custom_logic(rule.custom_logic, payload.data, parameters)
            if not isinstance(logic_result, dict):
                raise ValueError("custom logic must return a dictionary")
            for key, value in logic_result.items():
                parameters[key] = value
        agent_input = AgentInput(
            agent_id=rule.target_agent_id,
            parameters=parameters,
            context={"source": "webhook", "rule_id": rule.id, "rule_name": rule.name},
        )
        validation = self.validate(agent_input, rule.target_schema)
        if not validation.valid:
            assert validation.error is not None
            raise ValueError(validation.error.message)
        return agent_input

    def validate(self, agent_input: AgentInput, schema: dict[str, object] | None) -> ValidationResult:
        if schema is None:
            return ValidationResult(valid=True)
        required = schema.get("required", [])
        if isinstance(required, list):
            for field in required:
                if field not in agent_input.parameters:
                    return ValidationResult(
                        valid=False,
                        error=ValidationError(
                            code="INVALID_SCHEMA",
                            message=f"missing required field: {field}",
                            status_code=400,
                        ),
                    )
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for field, spec in properties.items():
                if field not in agent_input.parameters:
                    continue
                if not isinstance(spec, dict):
                    continue
                expected = spec.get("type")
                value = agent_input.parameters[field]
                if expected == "string" and not isinstance(value, str):
                    return _type_error(field, "string")
                if expected == "number" and not isinstance(value, int | float):
                    return _type_error(field, "number")
                if expected == "boolean" and not isinstance(value, bool):
                    return _type_error(field, "boolean")
                if expected == "object" and not isinstance(value, dict):
                    return _type_error(field, "object")
        return ValidationResult(valid=True)


def _extract_content_type(headers: dict[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value.split(";", 1)[0].strip().lower()
    return ""


def _xml_to_dict(node: ElementTree.Element) -> object:
    if len(node) == 0:
        return node.text or ""
    result: dict[str, object] = {}
    for child in node:
        tag = _strip_ns(child.tag)
        value = _xml_to_dict(child)
        if tag in result:
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[tag] = [existing, value]
        else:
            result[tag] = value
    return result


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _json_path_get(data: dict[str, object], path: str) -> object | None:
    if path == "$":
        return data
    if not path.startswith("$."):
        return None
    current: object = data
    for part in path[2:].split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _assign_path(target: dict[str, object], path: str, value: object) -> None:
    parts = path.split(".")
    current: dict[str, object] = target
    for key in parts[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[parts[-1]] = value


def _convert_value(value: object, transform: str | None) -> object:
    if transform is None:
        return value
    if transform == "string":
        return "" if value is None else str(value)
    if transform == "number":
        if value is None:
            return 0.0
        return float(value)
    if transform == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        return bool(value)
    if transform == "date":
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        raise ValueError("date transform requires datetime or ISO string")
    if transform == "json":
        if isinstance(value, str):
            return json.loads(value)
        return value
    raise ValueError(f"unsupported transform type: {transform}")


def _evaluate_custom_logic(expression: str, payload: dict[str, object], parameters: dict[str, object]) -> dict[str, object]:
    tree = ast.parse(expression, mode="eval")
    _validate_ast(tree)
    safe_globals = {"__builtins__": {}}
    safe_locals = {"payload": payload, "parameters": parameters}
    result = eval(compile(tree, "<transform-logic>", "eval"), safe_globals, safe_locals)
    if not isinstance(result, dict):
        raise ValueError("custom logic result must be dict")
    return result


def _validate_ast(node: ast.AST) -> None:
    allowed = (
        ast.Expression,
        ast.Dict,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Subscript,
        ast.Tuple,
        ast.List,
        ast.BinOp,
        ast.Add,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.IfExp,
        ast.UnaryOp,
        ast.USub,
    )
    for child in ast.walk(node):
        if not isinstance(child, allowed):
            raise ValueError("unsafe custom logic expression")
        if isinstance(child, ast.Name) and child.id not in {"payload", "parameters"}:
            raise ValueError("unsafe custom logic variable")


def _type_error(field: str, expected_type: str) -> ValidationResult:
    return ValidationResult(
        valid=False,
        error=ValidationError(
            code="INVALID_SCHEMA",
            message=f"field {field} must be {expected_type}",
            status_code=400,
        ),
    )
