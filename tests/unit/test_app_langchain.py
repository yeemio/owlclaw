"""LangChain integration tests for OwlClaw app API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from owlclaw import OwlClaw


class EchoRunnable:
    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"text": payload["text"]}


def _prepare_skill(tmp_path: Path, skill_name: str) -> None:
    (tmp_path / skill_name).mkdir(parents=True, exist_ok=True)
    (tmp_path / skill_name / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: LangChain skill\n---\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_register_langchain_runnable_and_execute(tmp_path: Path) -> None:
    _prepare_skill(tmp_path, "lc-skill")

    app = OwlClaw("lc-app")
    app.mount_skills(str(tmp_path))
    app.register_langchain_runnable(
        name="lc-skill",
        runnable=EchoRunnable(),
        description="Echo runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    result = await app.registry.invoke_handler("lc-skill", session={"text": "hello"})
    assert result["text"] == "hello"


@pytest.mark.asyncio
async def test_handler_decorator_supports_runnable_option(tmp_path: Path) -> None:
    _prepare_skill(tmp_path, "decorator-skill")

    app = OwlClaw("lc-app")
    app.mount_skills(str(tmp_path))

    @app.handler(
        "decorator-skill",
        runnable=EchoRunnable(),
        description="Decorator runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
    def _placeholder() -> None:
        return None

    result = await app.registry.invoke_handler("decorator-skill", session={"text": "world"})
    assert result["text"] == "world"


def test_register_langchain_runnable_requires_mount_skills() -> None:
    app = OwlClaw("lc-app")

    with pytest.raises(RuntimeError, match="mount_skills"):
        app.register_langchain_runnable(
            name="x",
            runnable=EchoRunnable(),
            description="x",
            input_schema={"type": "object", "properties": {}},
        )
