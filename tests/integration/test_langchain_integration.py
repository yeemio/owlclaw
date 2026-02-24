"""Integration tests for LangChain adapter end-to-end behavior."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest

from owlclaw import OwlClaw


class EchoRunnable:
    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"echo": payload["text"]}


class SlowRunnable:
    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.05)
        return {"echo": payload["text"]}


def _prepare_skill(tmp_path: Path, skill_name: str = "entry-monitor") -> None:
    (tmp_path / skill_name).mkdir(parents=True, exist_ok=True)
    (tmp_path / skill_name / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: Integration skill\n---\n",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _mock_langchain_version_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "owlclaw.integrations.langchain.check_langchain_version",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "owlclaw.integrations.langchain.adapter.check_langchain_version",
        lambda **kwargs: None,
    )


@pytest.mark.asyncio
async def test_end_to_end_langchain_execution(tmp_path: Path) -> None:
    _prepare_skill(tmp_path)
    app = OwlClaw("langchain-e2e")
    app.mount_skills(str(tmp_path))

    records: list[dict[str, Any]] = []

    async def record_langchain_execution(payload: dict[str, Any]) -> None:
        records.append(payload)

    app.record_langchain_execution = record_langchain_execution  # type: ignore[attr-defined]

    app.register_langchain_runnable(
        name="entry-monitor",
        runnable=EchoRunnable(),
        description="E2E runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    result = await app.registry.invoke_handler("entry-monitor", session={"text": "hello"})

    assert result["echo"] == "hello"
    assert len(records) == 1
    assert records[0]["status"] == "success"


@pytest.mark.asyncio
async def test_error_scenarios_validation_and_governance(tmp_path: Path) -> None:
    _prepare_skill(tmp_path)
    app = OwlClaw("langchain-e2e")
    app.mount_skills(str(tmp_path))

    async def validate_capability_execution(**kwargs: Any) -> dict[str, Any]:
        return {"allowed": False, "reason": "blocked", "status_code": 403}

    app.validate_capability_execution = validate_capability_execution  # type: ignore[attr-defined]

    app.register_langchain_runnable(
        name="entry-monitor",
        runnable=EchoRunnable(),
        description="E2E runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    blocked = await app.registry.invoke_handler("entry-monitor", session={"text": "hello"})
    assert blocked["error"]["status_code"] == 403

    app.validate_capability_execution = None  # type: ignore[attr-defined]
    invalid = await app.registry.invoke_handler("entry-monitor", session={"text": 1})
    assert invalid["error"]["status_code"] in {400, 500}


@pytest.mark.asyncio
async def test_timeout_and_fallback(tmp_path: Path) -> None:
    _prepare_skill(tmp_path, "entry-monitor")
    _prepare_skill(tmp_path, "morning-decision")
    app = OwlClaw("langchain-e2e")
    app.mount_skills(str(tmp_path))

    @app.handler("morning-decision")
    async def fallback_handler(session: dict[str, Any]) -> dict[str, Any]:
        return {"fallback": session.get("text", "")}

    app.register_langchain_runnable(
        name="entry-monitor",
        runnable=SlowRunnable(),
        description="Slow runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        timeout_seconds=0,
        fallback="morning-decision",
    )

    result = await app.registry.invoke_handler("entry-monitor", session={"text": "timeout"})

    assert result.get("_fallback_used") is True


@pytest.mark.asyncio
async def test_adapter_overhead_reasonable(tmp_path: Path) -> None:
    _prepare_skill(tmp_path)
    app = OwlClaw("langchain-e2e")
    app.mount_skills(str(tmp_path))

    app.register_langchain_runnable(
        name="entry-monitor",
        runnable=EchoRunnable(),
        description="Perf runnable",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    start = time.perf_counter()
    total = 50
    for _ in range(total):
        result = await app.registry.invoke_handler("entry-monitor", session={"text": "hello"})
        assert result["echo"] == "hello"
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / total) * 1000

    assert avg_ms < 20
