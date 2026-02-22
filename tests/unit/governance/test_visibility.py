"""Unit tests for VisibilityFilter and related types."""

import pytest

from owlclaw.governance.visibility import (
    CapabilityView,
    FilterResult,
    RunContext,
    VisibilityFilter,
)


@pytest.mark.asyncio
async def test_filter_result_default_reason():
    """FilterResult has empty reason by default."""
    r = FilterResult(visible=True)
    assert r.visible is True
    assert r.reason == ""


def test_register_evaluator_invalid_raises_type_error():
    vf = VisibilityFilter()
    with pytest.raises(TypeError, match="evaluator must provide"):
        vf.register_evaluator(object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_filter_empty_evaluators_returns_all():
    """With no evaluators, all capabilities pass."""
    vf = VisibilityFilter()
    caps = [
        CapabilityView("a", constraints={"x": 1}),
        CapabilityView("b", constraints={}),
    ]
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities(caps, "agent1", ctx)
    assert len(out) == 2
    assert [c.name for c in out] == ["a", "b"]


@pytest.mark.asyncio
async def test_filter_one_evaluator_hides_when_not_visible():
    """Single evaluator that hides one capability."""

    class HideB:
        async def evaluate(self, capability, agent_id, context):
            return FilterResult(visible=capability.name != "b")

    vf = VisibilityFilter()
    vf.register_evaluator(HideB())
    caps = [
        CapabilityView("a"),
        CapabilityView("b"),
        CapabilityView("c"),
    ]
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities(caps, "agent1", ctx)
    assert len(out) == 2
    assert [c.name for c in out] == ["a", "c"]


@pytest.mark.asyncio
async def test_filter_fail_open_on_evaluator_exception():
    """When an evaluator raises, capability remains visible (fail-open)."""

    class Raising:
        async def evaluate(self, capability, agent_id, context):
            raise ValueError("broken")

    vf = VisibilityFilter()
    vf.register_evaluator(Raising())
    caps = [CapabilityView("only")]
    ctx = RunContext(tenant_id="t1")
    out = await vf.filter_capabilities(caps, "agent1", ctx)
    assert len(out) == 1
    assert out[0].name == "only"


@pytest.mark.asyncio
async def test_filter_propagates_cancellation():
    """Cancellation must propagate instead of being swallowed as fail-open."""

    class Cancelling:
        async def evaluate(self, capability, agent_id, context):
            raise asyncio.CancelledError()

    import asyncio

    vf = VisibilityFilter()
    vf.register_evaluator(Cancelling())
    caps = [CapabilityView("only")]
    ctx = RunContext(tenant_id="t1")
    with pytest.raises(asyncio.CancelledError):
        await vf.filter_capabilities(caps, "agent1", ctx)


@pytest.mark.asyncio
async def test_capability_view_metadata():
    """CapabilityView.metadata exposes owlclaw.constraints."""
    cap = CapabilityView(
        "x",
        task_type="t1",
        constraints={"max_daily": 10},
        focus=["inventory_monitor"],
        risk_level="high",
        requires_confirmation=True,
    )
    assert cap.metadata["owlclaw"]["constraints"] == {"max_daily": 10}
    assert cap.metadata["owlclaw"]["task_type"] == "t1"
    assert cap.metadata["owlclaw"]["focus"] == ["inventory_monitor"]
    assert cap.metadata["owlclaw"]["risk_level"] == "high"
    assert cap.metadata["owlclaw"]["requires_confirmation"] is True
