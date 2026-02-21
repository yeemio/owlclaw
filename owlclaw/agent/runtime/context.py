"""AgentRunContext — single-run context passed through the entire Agent pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRunContext:
    """Context for a single Agent run.

    Created once per invocation and threaded through identity loading,
    memory recall, skill selection, and the decision loop.

    Attributes:
        agent_id: Stable identifier for the Agent (usually the app name).
        run_id: UUID for this specific run; auto-generated when omitted.
        trigger: Source of this run — ``"cron"``, ``"schedule_once"``,
            ``"webhook"``, ``"heartbeat"``, ``"manual"``, etc.
        payload: Arbitrary JSON-serialisable context from the trigger source.
        focus: Optional tag from ``@app.cron(focus=...)`` or
            ``schedule_once``; narrows Skill loading to relevant subset.
        tenant_id: Multi-tenancy identifier; defaults to ``"default"``.
    """

    agent_id: str
    trigger: str
    payload: dict[str, Any] = field(default_factory=dict)
    focus: str | None = None
    tenant_id: str = "default"
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
