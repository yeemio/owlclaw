from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from owlclaw.triggers.webhook import GovernanceClient, GovernanceContext


class _TimeoutPolicy:
    async def check_permission(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        await asyncio.sleep(0.2)
        return {"allowed": True}

    async def check_rate_limit(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        await asyncio.sleep(0.2)
        return {"allowed": True}


class _FixedPolicy:
    def __init__(self, permission: dict[str, Any], rate_limit: dict[str, Any]) -> None:
        self._permission = permission
        self._rate_limit = rate_limit

    async def check_permission(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        return self._permission

    async def check_rate_limit(self, context: GovernanceContext) -> dict[str, Any]:  # noqa: ARG002
        return self._rate_limit


@dataclass
class _AuditSink:
    events: list[dict[str, Any]] = field(default_factory=list)

    async def record(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def _context() -> GovernanceContext:
    return GovernanceContext(
        tenant_id="default",
        endpoint_id="ep-1",
        agent_id="agent-1",
        request_id="req-1",
        source_ip="127.0.0.1",
        user_agent="pytest",
    )


@pytest.mark.asyncio
async def test_governance_client_handles_timeout() -> None:
    client = GovernanceClient(_TimeoutPolicy(), timeout_seconds=0.01)
    result = await client.validate_execution(_context())

    assert not result.valid
    assert result.error is not None
    assert result.error.status_code == 503


@pytest.mark.asyncio
async def test_governance_client_applies_policy_limits() -> None:
    policy = _FixedPolicy(
        permission={
            "allowed": False,
            "status_code": 403,
            "reason": "quota exceeded",
            "policy_limits": {"daily_quota": 100},
        },
        rate_limit={"allowed": True},
    )
    client = GovernanceClient(policy)
    result = await client.validate_execution(_context())

    assert not result.valid
    assert result.error is not None
    assert result.error.status_code == 403
    assert result.error.details == {"policy_limits": {"daily_quota": 100}}


@pytest.mark.asyncio
async def test_governance_client_audit_log_is_complete() -> None:
    policy = _FixedPolicy(permission={"allowed": True}, rate_limit={"allowed": True})
    sink = _AuditSink()
    client = GovernanceClient(policy, audit_sink=sink)

    result = await client.validate_execution(_context())
    assert result.valid
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["tenant_id"] == "default"
    assert event["endpoint_id"] == "ep-1"
    assert event["agent_id"] == "agent-1"
    assert event["request_id"] == "req-1"
    assert event["allowed"] is True
    assert event["status_code"] == 200
