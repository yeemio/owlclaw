from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from owlclaw.app import OwlClaw
from owlclaw.capabilities.bindings import BindingTool
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader, auto_register_binding_tools


def _write_skill(path: Path) -> None:
    path.write_text(
        """---
name: demo-skill
description: demo skill for binding
metadata:
  tools_schema:
    fetch-order:
      description: fetch order from service
      parameters:
        type: object
      binding:
        type: http
        mode: active
        method: GET
        url: https://svc.local/orders/{order_id}
---
# Demo
""",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_mount_skills_auto_registers_binding_tool_and_invokes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skills_dir = tmp_path / "capabilities" / "demo-skill"
    skills_dir.mkdir(parents=True)
    _write_skill(skills_dir / "SKILL.md")

    async def fake_execute(self: Any, config: Any, parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN401
        return {"status": "ok", "parameters": parameters, "type": config.type}

    monkeypatch.setattr("owlclaw.capabilities.bindings.http_executor.HTTPBindingExecutor.execute", fake_execute)

    app = OwlClaw("binding-app")
    app.mount_skills(str(tmp_path / "capabilities"))

    assert app.registry is not None
    handler = app.registry.handlers.get("fetch-order")
    assert isinstance(handler, BindingTool)

    result = await app.registry.invoke_handler("fetch-order", order_id=42)
    assert result["status"] == "ok"
    assert result["parameters"] == {"order_id": 42}


@pytest.mark.asyncio
async def test_handler_registration_overrides_auto_binding_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skills_dir = tmp_path / "capabilities" / "demo-skill"
    skills_dir.mkdir(parents=True)
    _write_skill(skills_dir / "SKILL.md")

    async def fake_execute(self: Any, config: Any, parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN401
        return {"status": "binding", "parameters": parameters}

    monkeypatch.setattr("owlclaw.capabilities.bindings.http_executor.HTTPBindingExecutor.execute", fake_execute)

    app = OwlClaw("binding-app")
    app.mount_skills(str(tmp_path / "capabilities"))

    @app.handler("fetch-order")
    async def manual_handler(order_id: int) -> dict[str, Any]:
        return {"status": "manual", "order_id": order_id}

    assert app.registry is not None
    assert app.registry.handlers["fetch-order"] is manual_handler
    result = await app.registry.invoke_handler("fetch-order", order_id=7)
    assert result == {"status": "manual", "order_id": 7}


def test_auto_register_binding_tools_respects_existing_handler(tmp_path: Path) -> None:
    skills_dir = tmp_path / "capabilities" / "demo-skill"
    skills_dir.mkdir(parents=True)
    _write_skill(skills_dir / "SKILL.md")

    loader = SkillsLoader(tmp_path / "capabilities")
    loader.scan()
    registry = CapabilityRegistry(loader)

    def existing_handler(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    registry.register_handler("fetch-order", existing_handler)
    registered = auto_register_binding_tools(loader, registry)
    assert registered == []
    assert registry.handlers["fetch-order"] is existing_handler
