"""Unit tests for Router and ModelSelection."""

import pytest

from owlclaw.governance.router import Router
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
async def test_router_rule_match_with_trimmed_task_type():
    r = Router(
        {
            "rules": [
                {
                    "task_type": " trading_decision ",
                    "model": "gpt-4o",
                    "fallback": [],
                },
            ],
            "default_model": "gpt-4o-mini",
        }
    )
    ctx = RunContext(tenant_id="t1")
    sel = await r.select_model(" trading_decision ", ctx)
    assert sel.model == "gpt-4o"


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


@pytest.mark.asyncio
async def test_handle_model_failure_skips_invalid_fallback_entries():
    r = Router({})
    next_model = await r.handle_model_failure(
        "gpt-4o",
        "trading_decision",
        Exception("rate limit"),
        ["", "  ", "gpt-4o-mini", 123],  # type: ignore[list-item]
    )
    assert next_model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_router_handles_non_dict_config() -> None:
    r = Router(None)  # type: ignore[arg-type]
    ctx = RunContext(tenant_id="t1")
    sel = await r.select_model("any", ctx)
    assert sel.model == "gpt-4o-mini"
    assert sel.fallback == []


@pytest.mark.asyncio
async def test_router_ignores_invalid_rules_and_normalizes_fallback() -> None:
    r = Router(
        {
            "rules": [
                "bad-shape",
                {
                    "task_type": "trading_decision",
                    "model": "  ",
                    "fallback": [" gpt-4o-mini ", "", 123],  # type: ignore[list-item]
                },
            ],
            "default_model": "gpt-4o",
        }
    )
    ctx = RunContext(tenant_id="t1")
    sel = await r.select_model("trading_decision", ctx)
    assert sel.model == "gpt-4o"
    assert sel.fallback == ["gpt-4o-mini"]


@pytest.mark.asyncio
async def test_router_reload_config_updates_rules_and_default() -> None:
    r = Router({"default_model": "gpt-4o-mini"})
    ctx = RunContext(tenant_id="t1")

    before = await r.select_model("trading_decision", ctx)
    assert before.model == "gpt-4o-mini"

    r.reload_config(
        {
            "rules": [
                {
                    "task_type": "trading_decision",
                    "model": "gpt-4o",
                    "fallback": ["gpt-4o-mini"],
                }
            ],
            "default_model": "gpt-4.1-mini",
        }
    )

    after = await r.select_model("trading_decision", ctx)
    assert after.model == "gpt-4o"
    assert after.fallback == ["gpt-4o-mini"]

    unmatched = await r.select_model("unknown", ctx)
    assert unmatched.model == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_router_reload_config_with_invalid_payload_falls_back_to_defaults() -> None:
    r = Router(
        {
            "rules": [{"task_type": "x", "model": "gpt-4o"}],
            "default_model": "gpt-4o",
        }
    )
    ctx = RunContext(tenant_id="t1")

    r.reload_config(None)  # type: ignore[arg-type]
    sel = await r.select_model("x", ctx)
    assert sel.model == "gpt-4o-mini"
    assert sel.fallback == []
