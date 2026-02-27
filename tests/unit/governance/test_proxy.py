"""Unit tests for GovernanceProxy."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from owlclaw.governance.proxy import GovernanceProxy, GovernanceRejectedError


@pytest.mark.asyncio
async def test_proxy_allows_successful_call_and_returns_dict() -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"id": "r1", "usage": {"total_tokens": 500}}

    proxy = GovernanceProxy(llm_call=_ok_call, daily_limit_usd=Decimal("10"))
    response = await proxy.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        caller="mionyee.ai.trading_decision",
    )
    assert response["id"] == "r1"


@pytest.mark.asyncio
async def test_proxy_blocks_when_daily_budget_exhausted() -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"usage": {"total_tokens": 2000}}

    proxy = GovernanceProxy(llm_call=_ok_call, daily_limit_usd=Decimal("0.001"))
    await proxy.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "first"}],
        caller="mionyee.ai.trading_decision",
    )
    with pytest.raises(GovernanceRejectedError, match="budget_exhausted_daily"):
        await proxy.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "second"}],
            caller="mionyee.ai.trading_decision",
        )


@pytest.mark.asyncio
async def test_proxy_blocks_when_rate_limit_exceeded() -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"usage": {"total_tokens": 1}}

    proxy = GovernanceProxy(llm_call=_ok_call, default_qps=1)
    await proxy.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "first"}],
        caller="mionyee.ai.trading_decision",
    )
    with pytest.raises(GovernanceRejectedError, match="rate_limited"):
        await proxy.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "second"}],
            caller="mionyee.ai.trading_decision",
        )


@pytest.mark.asyncio
async def test_proxy_opens_circuit_after_consecutive_failures() -> None:
    async def _fail_call(**_: object) -> dict[str, object]:
        raise RuntimeError("provider down")

    proxy = GovernanceProxy(llm_call=_fail_call, failure_threshold=2, recovery_timeout_seconds=60)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await proxy.acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "x"}],
                caller="mionyee.ai.trading_decision",
            )
    with pytest.raises(GovernanceRejectedError, match="circuit_open"):
        await proxy.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "x"}],
            caller="mionyee.ai.trading_decision",
        )


@pytest.mark.asyncio
async def test_proxy_passthrough_on_gate_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok_call(**_: object) -> dict[str, object]:
        return {"ok": True}

    proxy = GovernanceProxy(llm_call=_ok_call, passthrough_on_error=True)

    def _broken_budget(_: str) -> None:
        raise ValueError("unexpected gate failure")

    monkeypatch.setattr(proxy, "_check_budget", _broken_budget)
    response = await proxy.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "x"}],
        caller="mionyee.ai.trading_decision",
    )
    assert response["ok"] is True


def test_proxy_from_config_loads_governance_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "owlclaw.yaml"
    cfg.write_text(
        """
governance:
  budget:
    daily_limit_usd: 3.5
    monthly_limit_usd: 42
  rate_limit:
    default_qps: 7
    per_service:
      mionyee.ai.trading_decision: 2
  circuit_breaker:
    failure_threshold: 4
    recovery_timeout_seconds: 99
    half_open_max_calls: 5
  proxy:
    tenant_id: mionyee
    agent_id: mionyee.proxy
""",
        encoding="utf-8",
    )
    proxy = GovernanceProxy.from_config(str(cfg))
    assert proxy.daily_limit_usd == Decimal("3.5")
    assert proxy.monthly_limit_usd == Decimal("42")
    assert proxy.default_qps == 7
    assert proxy.per_service_qps["mionyee.ai.trading_decision"] == 2
    assert proxy.failure_threshold == 4
    assert proxy.recovery_timeout_seconds == 99
    assert proxy.half_open_max_calls == 5
    assert proxy.tenant_id == "mionyee"
    assert proxy.agent_id == "mionyee.proxy"
