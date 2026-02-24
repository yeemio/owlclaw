"""HTTP binding executor implementation."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from owlclaw.capabilities.bindings.credential import CredentialResolver
from owlclaw.capabilities.bindings.executor import BindingExecutor
from owlclaw.capabilities.bindings.schema import BindingConfig, HTTPBindingConfig

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class HTTPBindingExecutor(BindingExecutor):
    """Execute HTTP bindings in active or shadow mode."""

    def __init__(self, credential_resolver: CredentialResolver | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._credential_resolver = credential_resolver or CredentialResolver()
        self._transport = transport

    async def execute(self, config: BindingConfig, parameters: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(config, HTTPBindingConfig):
            raise TypeError("HTTPBindingExecutor requires HTTPBindingConfig")
        method = config.method.upper()
        url = self._render_url(config.url, parameters)
        headers = self._render_headers(config.headers)
        body = self._render_body(config.body_template, parameters)

        if config.mode == "shadow" and method in WRITE_METHODS:
            return {
                "status": "shadow",
                "mode": "shadow",
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "sent": False,
            }

        response = await self._request_with_retry(config, method, url, headers, body)
        payload = self._safe_json(response)
        mapped = self._apply_response_mapping(config.response_mapping, response.status_code, payload)

        return {
            "status": "ok",
            "mode": config.mode,
            "status_code": response.status_code,
            "data": mapped,
            "raw": payload,
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        method = str(config.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            errors.append("method must be one of GET/POST/PUT/PATCH/DELETE")
        if not str(config.get("url", "")).strip():
            errors.append("url is required")
        return errors

    @property
    def supported_modes(self) -> list[str]:
        return ["active", "shadow"]

    async def _request_with_retry(
        self,
        config: HTTPBindingConfig,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> httpx.Response:
        attempts = max(int(config.retry.max_attempts), 1)
        delay = max(int(config.retry.backoff_ms), 1) / 1000.0
        timeout_seconds = max(int(config.timeout_ms), 1) / 1000.0

        last_exception: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds, transport=self._transport) as client:
                    response = await client.request(method=method, url=url, headers=headers, json=body)
                return response
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exception = exc
                if attempt == attempts:
                    break
                await asyncio.sleep(delay)
                delay *= float(config.retry.backoff_multiplier)
        raise TimeoutError(f"http binding request failed after {attempts} attempts") from last_exception

    def _render_url(self, template: str, parameters: dict[str, Any]) -> str:
        rendered = template
        for key, value in parameters.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        return rendered

    def _render_headers(self, headers: dict[str, str]) -> dict[str, str]:
        return {key: self._credential_resolver.resolve(value) for key, value in headers.items()}

    def _render_body(self, body_template: dict[str, Any] | None, parameters: dict[str, Any]) -> dict[str, Any] | None:
        if body_template is None:
            return None

        def _resolve(value: Any) -> Any:
            if isinstance(value, str):
                rendered = value
                for key, item in parameters.items():
                    rendered = rendered.replace(f"{{{key}}}", str(item))
                return rendered
            if isinstance(value, dict):
                return {k: _resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_resolve(v) for v in value]
            return value

        resolved = _resolve(body_template)
        return resolved if isinstance(resolved, dict) else None

    def _apply_response_mapping(self, mapping: dict[str, Any], status_code: int, payload: Any) -> Any:
        status_map = mapping.get("status_codes", {}) if isinstance(mapping, dict) else {}
        mapped_status = status_map.get(str(status_code))
        if mapped_status and mapped_status != "success":
            return {"error_type": mapped_status, "status_code": status_code}

        path = mapping.get("path") if isinstance(mapping, dict) else None
        if isinstance(path, str) and path.startswith("$."):
            return self._extract_json_path(payload, path)
        return payload

    @staticmethod
    def _extract_json_path(payload: Any, path: str) -> Any:
        current = payload
        for part in path[2:].split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    @staticmethod
    def _safe_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}

