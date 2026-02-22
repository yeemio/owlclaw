"""Integration tests: OwlClaw app with governance (VisibilityFilter, Router, Ledger)."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlclaw.app import OwlClaw


@pytest.fixture
def app_with_skills(tmp_path):
    """OwlClaw app with one skill mounted."""
    skill_dir = tmp_path / "entry-monitor"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: entry-monitor
description: Check entry opportunities
owlclaw:
  task_type: trading_decision
  constraints:
    trading_hours_only: true
---
# Guide
"""
    )
    app = OwlClaw("test")
    app.mount_skills(str(tmp_path))
    return app


@pytest.mark.asyncio
async def test_get_visible_capabilities_without_governance_returns_all(app_with_skills):
    """Without governance config, get_visible_capabilities returns all from registry."""
    app = app_with_skills

    @app.handler("entry-monitor")
    async def handler(session):
        return {}

    out = await app.get_visible_capabilities("agent1", "default")
    assert len(out) == 1
    assert out[0]["name"] == "entry-monitor"


@pytest.mark.asyncio
async def test_get_visible_capabilities_with_visibility_filter(app_with_skills):
    """With governance (visibility only), filter is applied."""
    app = app_with_skills
    app.configure(
        governance={
            "visibility": {"time": {"timezone": "UTC"}},
            "router": {"default_model": "gpt-4o-mini"},
        }
    )

    @app.handler("entry-monitor")
    async def handler(session):
        return {}

    out = await app.get_visible_capabilities("agent1", "default")
    # TimeConstraint with trading_hours_only: depends on current time; at least we get a list
    assert isinstance(out, list)
    assert all(isinstance(c, dict) and "name" in c for c in out)


@pytest.mark.asyncio
async def test_get_visible_capabilities_passes_confirmed_capabilities(app_with_skills):
    """confirmed_capabilities should be forwarded to visibility RunContext."""
    app = app_with_skills
    app.configure(governance={"visibility": {"time": {}}, "router": {}})
    app._ensure_governance()
    app._visibility_filter.filter_capabilities = AsyncMock(return_value=[])  # type: ignore[union-attr]

    @app.handler("entry-monitor")
    async def handler(session):
        return {}

    await app.get_visible_capabilities(
        "agent1",
        "default",
        confirmed_capabilities=["entry-monitor"],
    )
    run_ctx = app._visibility_filter.filter_capabilities.call_args.args[2]  # type: ignore[union-attr]
    assert run_ctx.confirmed_capabilities == {"entry-monitor"}


@pytest.mark.asyncio
async def test_get_visible_capabilities_coerces_requires_confirmation_string(app_with_skills):
    """requires_confirmation='false' should not be treated as true in capability view."""
    app = app_with_skills

    @app.handler("entry-monitor")
    async def handler(session):
        return {}

    original = app.registry.list_capabilities  # type: ignore[union-attr]

    def _patched_caps():  # type: ignore[no-untyped-def]
        rows = original()
        rows[0]["requires_confirmation"] = "false"
        return rows

    app.registry.list_capabilities = _patched_caps  # type: ignore[assignment,union-attr]
    out = await app.get_visible_capabilities("agent1", "default")
    assert out[0]["requires_confirmation"] is False


@pytest.mark.asyncio
async def test_get_visible_capabilities_risk_confirmation_gate(tmp_path):
    """High-risk capability should be hidden until explicitly confirmed."""
    skill_dir = tmp_path / "place-order"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: place-order
description: Place trade order
owlclaw:
  risk_level: high
  requires_confirmation: true
---
# Guide
"""
    )
    app = OwlClaw("risk-app")
    app.mount_skills(str(tmp_path))
    app.configure(
        governance={
            "visibility": {
                "time": {},
                "risk_confirmation": {"enforce_high_risk_confirmation": True},
            },
            "router": {},
        }
    )

    @app.handler("place-order")
    async def handler(session):
        return {}

    hidden = await app.get_visible_capabilities("agent1", "default")
    assert hidden == []

    visible = await app.get_visible_capabilities(
        "agent1",
        "default",
        confirmed_capabilities=["place-order"],
    )
    assert len(visible) == 1
    assert visible[0]["name"] == "place-order"


@pytest.mark.asyncio
async def test_get_model_selection_with_router(app_with_skills):
    """With router config, get_model_selection returns ModelSelection."""
    app = app_with_skills
    app.configure(
        governance={
            "router": {
                "default_model": "gpt-4o-mini",
                "rules": [
                    {"task_type": "trading_decision", "model": "gpt-4o", "fallback": []},
                ],
            },
        }
    )
    sel = await app.get_model_selection("trading_decision", "default")
    assert sel is not None
    assert sel.model == "gpt-4o"


@pytest.mark.asyncio
async def test_record_execution_with_ledger(app_with_skills):
    """With Ledger (mock session_factory), record_execution enqueues."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.add_all = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=cm)
    app = app_with_skills
    app.configure(
        governance={
            "session_factory": session_factory,
            "router": {},
            "visibility": {"time": {}},
        }
    )
    await app.start_governance()
    await app.record_execution(
        tenant_id="default",
        agent_id="agent1",
        run_id="run1",
        capability_name="entry-monitor",
        task_type="trading_decision",
        input_params={},
        output_result={},
        decision_reasoning=None,
        execution_time_ms=100,
        llm_model="gpt-4o-mini",
        llm_tokens_input=10,
        llm_tokens_output=5,
        estimated_cost=Decimal("0.001"),
        status="success",
        error_message=None,
    )
    assert app._ledger is not None
    assert app._ledger._write_queue.qsize() == 1
    await app.stop_governance()
