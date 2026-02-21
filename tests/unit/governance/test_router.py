"""Unit tests for Router and ModelSelection."""

import pytest

from owlclaw.governance.router import ModelSelection, Router
from owlclaw.governance.visibility import RunContext


@pytest.mark.asyncio
async def test_router_default_model():
    """Router returns default_model when no rule matches."""
    r = Router({"default_model": "gpt-4o-mini"})
    ctx = RunContext(tenant_id="t1")
    sel = await r.select_model("unknown_type", ctx)
    assert sel.model == "gpt-4o-mini"
    assert sel.fallback == []


@pytest.mark.asyncio
async def test_router_rule_match():
    """Router returns rule model and fallback for matching task_type."""
    r = Router({
        "rules": [
            {
                "task_type": "trading_decision",
                "model": "gpt-4o",
                "fallback": ["gpt-4o-mini", "gpt-3.5-turbo"],
            },
        ],
        "default_model": "gpt-4o-mini",
    })
    ctx = RunContext(tenant_id="t1")
    sel = await r.select_model("trading_decision", ctx)
    assert sel.model == "gpt-4o"
    assert sel.fallback == ["gpt-4o-mini", "gpt-3.5-turbo"]


@pytest.mark.asyncio
async def test_handle_model_failure_returns_next():
    """handle_model_failure returns first fallback model."""
    r = Router({})
    next_model = await r.handle_model_failure(
        "gpt-4o",
        "trading_decision",
        Exception("rate limit"),
        ["gpt-4o-mini", "gpt-3.5-turbo"],
    )
    assert next_model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_handle_model_failure_empty_chain_returns_none():
    """handle_model_failure returns None when fallback chain is empty."""
    r = Router({})
    next_model = await r.handle_model_failure(
        "gpt-4o",
        "trading_decision",
        Exception("fail"),
        [],
    )
    assert next_model is None
