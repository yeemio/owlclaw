"""Unit tests for in-memory approval queue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from owlclaw.governance.approval_queue import (
    ApprovalStatus,
    InMemoryApprovalQueue,
)


@pytest.mark.asyncio
async def test_create_and_list_pending_requests() -> None:
    queue = InMemoryApprovalQueue(timeout_seconds=3600)
    request = await queue.create(
        tenant_id="default",
        agent_id="agent-1",
        skill_name="inventory-check",
        suggestion={"action": "reorder"},
        reasoning="stock below threshold",
    )
    rows = await queue.list(tenant_id="default")
    assert len(rows) == 1
    assert rows[0].id == request.id
    assert rows[0].status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_approve_and_modify_flow() -> None:
    queue = InMemoryApprovalQueue(timeout_seconds=3600)
    request = await queue.create(
        tenant_id="default",
        agent_id="agent-1",
        skill_name="reorder-decision",
        suggestion={"sku": "WIDGET-42", "qty": 100},
    )
    approved = await queue.approve(request.id, approver="ops-a")
    assert approved.status == ApprovalStatus.APPROVED
    assert approved.approver == "ops-a"

    request2 = await queue.create(
        tenant_id="default",
        agent_id="agent-1",
        skill_name="reorder-decision",
        suggestion={"sku": "WIDGET-42", "qty": 100},
    )
    modified = await queue.approve(request2.id, approver="ops-b", modified_payload={"sku": "WIDGET-42", "qty": 80})
    assert modified.status == ApprovalStatus.MODIFIED
    assert modified.approved_payload == {"sku": "WIDGET-42", "qty": 80}


@pytest.mark.asyncio
async def test_reject_and_expire_flow() -> None:
    queue = InMemoryApprovalQueue(timeout_seconds=1)
    request = await queue.create(
        tenant_id="default",
        agent_id="agent-1",
        skill_name="anomaly-alert",
        suggestion={"action": "notify"},
    )
    rejected = await queue.reject(request.id, approver="ops-c")
    assert rejected.status == ApprovalStatus.REJECTED

    expired_request = await queue.create(
        tenant_id="default",
        agent_id="agent-1",
        skill_name="daily-report",
        suggestion={"action": "publish"},
    )
    expired_request.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired_count = await queue.expire_pending()
    assert expired_count == 1
    rows = await queue.list(tenant_id="default", status=ApprovalStatus.EXPIRED)
    assert any(row.id == expired_request.id for row in rows)
