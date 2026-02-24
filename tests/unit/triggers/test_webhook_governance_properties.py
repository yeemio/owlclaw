from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.triggers.webhook import GovernanceClient, GovernanceContext


@dataclass
class _Policy:
    permission_allowed: bool
    permission_reason: str
    limits: dict[str, Any]

    async def check_permission(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        if self.permission_allowed:
            return {"allowed": True}
        return {
            "allowed": False,
            "status_code": 403,
            "reason": self.permission_reason,
            "policy_limits": self.limits,
        }

    async def check_rate_limit(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        return {"allowed": True}


def _context() -> GovernanceContext:
    return GovernanceContext(
        tenant_id="default",
        endpoint_id="ep-prop",
        agent_id="agent-prop",
        request_id="req-prop",
    )


@given(reason=st.text(min_size=1, max_size=40))
@settings(max_examples=35, deadline=None)
def test_property_governance_rejection_returns_403(reason: str) -> None:
    """Feature: triggers-webhook, Property 13: 治理层拒绝返回 403."""

    async def _run() -> None:
        client = GovernanceClient(_Policy(permission_allowed=False, permission_reason=reason, limits={}))
        result = await client.validate_execution(_context())
        assert not result.valid
        assert result.error is not None
        assert result.error.status_code == 403

    asyncio.run(_run())


@given(permission_allowed=st.booleans())
@settings(max_examples=35, deadline=None)
def test_property_execution_requests_governance_validation(permission_allowed: bool) -> None:
    """Feature: triggers-webhook, Property 25: 执行前请求治理验证."""

    async def _run() -> None:
        client = GovernanceClient(_Policy(permission_allowed=permission_allowed, permission_reason="denied", limits={}))
        result = await client.validate_execution(_context())
        assert result.valid is permission_allowed

    asyncio.run(_run())


@given(
    limit_key=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=12),
    limit_value=st.integers(min_value=1, max_value=1000),
)
@settings(max_examples=35, deadline=None)
def test_property_governance_policy_limits_are_applied(limit_key: str, limit_value: int) -> None:
    """Feature: triggers-webhook, Property 26: 应用治理策略限制."""

    async def _run() -> None:
        limits = {limit_key: limit_value}
        client = GovernanceClient(_Policy(permission_allowed=False, permission_reason="limited", limits=limits))
        result = await client.validate_execution(_context())
        assert not result.valid
        assert result.error is not None
        assert result.error.details == {"policy_limits": limits}

    asyncio.run(_run())
