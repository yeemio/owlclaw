"""Tests for A/B test runner and auto migration_weight adjustment."""

from __future__ import annotations

import pytest

from owlclaw.e2e.ab_test import ABTestResult, ABTestRunner


@pytest.mark.asyncio
async def test_should_use_agent_respects_weight(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = ABTestRunner()
    monkeypatch.setattr("owlclaw.e2e.ab_test.random.random", lambda: 0.05)
    assert await runner.should_use_agent(0.1) is True
    monkeypatch.setattr("owlclaw.e2e.ab_test.random.random", lambda: 0.9)
    assert await runner.should_use_agent(0.1) is False


@pytest.mark.asyncio
async def test_statistical_test_recommends_weight_increase() -> None:
    runner = ABTestRunner()
    for index in range(20):
        await runner.record_outcome(f"a-{index}", "agent-1", "agent", {"conversion_rate": 0.9})
        await runner.record_outcome(f"f-{index}", "agent-1", "fallback", {"conversion_rate": 0.4})

    result = await runner.statistical_test("agent-1", "conversion_rate")
    assert result.significant is True
    assert result.recommendation == "increase_weight"
    assert result.agent_mean > result.fallback_mean


@pytest.mark.asyncio
async def test_auto_adjust_weight_rollback_on_regression() -> None:
    runner = ABTestRunner()
    result = ABTestResult(
        agent_mean=0.2,
        fallback_mean=0.6,
        p_value=0.01,
        significant=True,
        recommendation="rollback_weight",
    )
    adjusted = await runner.auto_adjust_weight(0.6, result)
    assert adjusted == 0.0

