"""Cron trigger registry — persistent Agent-driven cron scheduling.

Provides CronTriggerRegistry and associated data models for registering
@app.cron decorated functions, validating cron expressions via croniter,
and lifecycle management of scheduled tasks.

Hatchet workflow creation is deferred to a separate start() phase so that
registration is always safe to call at import time even without a live
Hatchet connection.
"""

from __future__ import annotations

import inspect
import logging
import random
import traceback as _traceback
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from croniter import croniter  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from owlclaw.agent.runtime import AgentRuntime
    from owlclaw.governance.ledger import Ledger
    from owlclaw.integrations.hatchet import HatchetClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models — Task 1
# ---------------------------------------------------------------------------


class ExecutionStatus(str, Enum):
    """Execution status for a single cron run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    FALLBACK = "fallback"


@dataclass
class CronTriggerConfig:
    """Configuration for a single cron trigger."""

    event_name: str
    expression: str
    description: str | None = None

    # Agent guidance
    focus: str | None = None

    # Fallback / migration
    fallback_handler: Callable | None = None
    fallback_strategy: str = "on_failure"
    migration_weight: float = 1.0

    # Governance
    max_cost_per_run: float | None = None
    max_daily_cost: float | None = None
    max_duration: int | None = None
    cooldown_seconds: int = 0
    max_daily_runs: int | None = None

    # Reliability
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # Metadata
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class CronExecution:
    """Record of a single cron trigger execution."""

    execution_id: str
    event_name: str
    triggered_at: datetime
    status: ExecutionStatus
    context: dict[str, Any]
    decision_mode: str = "agent"

    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    agent_run_id: str | None = None
    llm_calls: int = 0
    cost_usd: float = 0.0

    governance_checks: dict[str, Any] = field(default_factory=dict)
    skip_reason: str | None = None

    error_message: str | None = None
    error_traceback: str | None = None
    retry_count: int = 0


class FocusManager:
    """Load and format skills with optional focus filtering."""

    def __init__(self, skills_manager: Any) -> None:
        self.skills_manager = skills_manager

    async def load_skills_for_focus(self, focus: str | None) -> list[Any]:
        """Load skills and filter by focus when provided."""
        list_skills = getattr(self.skills_manager, "list_skills", None)
        if not callable(list_skills):
            return []
        skills = list_skills()
        if inspect.isawaitable(skills):
            skills = await skills
        if not isinstance(skills, list):
            return []
        if not focus:
            return [skill for skill in skills if hasattr(skill, "name") and hasattr(skill, "description")]
        normalized_focus = focus.strip().lower()
        if not normalized_focus:
            return [skill for skill in skills if hasattr(skill, "name") and hasattr(skill, "description")]
        return [skill for skill in skills if self._skill_matches_focus(skill, normalized_focus)]

    def _skill_matches_focus(self, skill: Any, focus: str) -> bool:
        """Return whether a single skill matches the given focus."""
        target = focus.strip().lower()
        if not target:
            return True
        try:
            direct_focus = getattr(skill, "focus", [])
            direct_values: list[str]
            if isinstance(direct_focus, str):
                direct_values = [direct_focus]
            elif isinstance(direct_focus, list):
                direct_values = [str(value) for value in direct_focus]
            else:
                direct_values = []
            if any(value.strip().lower() == target for value in direct_values if value.strip()):
                return True

            metadata = getattr(skill, "metadata", {})
            if isinstance(metadata, dict):
                meta_focus = metadata.get("focus", [])
                if isinstance(meta_focus, str):
                    meta_values = [meta_focus]
                elif isinstance(meta_focus, list):
                    meta_values = [str(value) for value in meta_focus]
                else:
                    meta_values = []
                if any(value.strip().lower() == target for value in meta_values if value.strip()):
                    return True
        except Exception:
            return False
        return False

    def build_agent_prompt(self, focus: str | None, skills: list[Any]) -> str:
        """Build a prompt snippet describing current focus and available skills."""
        prompt_parts: list[str] = []
        if focus and focus.strip():
            normalized_focus = focus.strip()
            prompt_parts.append(f"Current focus: {normalized_focus}")
            prompt_parts.append(f"You should prioritize actions related to {normalized_focus}.")
        else:
            prompt_parts.append("Current focus: none")
        prompt_parts.append("")
        prompt_parts.append("Available skills:")
        if not skills:
            prompt_parts.append("- (none)")
            return "\n".join(prompt_parts)
        for skill in skills:
            name = str(getattr(skill, "name", "")).strip()
            description = str(getattr(skill, "description", "")).strip()
            if not name:
                continue
            prompt_parts.append(f"- {name}: {description}")
        return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# CronTriggerRegistry — Task 2
# ---------------------------------------------------------------------------


class CronTriggerRegistry:
    """Registry for cron triggers.

    Manages validation, storage, and lifecycle of all @app.cron decorated
    functions.  Hatchet workflow objects are stored separately and populated
    on start().
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self._triggers: dict[str, CronTriggerConfig] = {}
        self._hatchet_workflows: dict[str, Callable[..., Any]] = {}
        self._hatchet_client: HatchetClient | None = None
        self._ledger: Ledger | None = None
        self._tenant_id: str = "default"
        self._recent_executions: dict[str, deque[tuple[str, float | None]]] = {}

    # ------------------------------------------------------------------
    # Task 2.2 — cron expression validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_cron_expression(expression: str) -> bool:
        """Return True if *expression* is a valid 5-field cron expression."""
        try:
            return bool(croniter.is_valid(expression))
        except Exception:
            return False

    @staticmethod
    def _normalize_event_name(event_name: str) -> str:
        if not isinstance(event_name, str):
            raise ValueError("event_name must be a non-empty string")
        normalized = event_name.strip()
        if not normalized:
            raise ValueError("event_name must not be empty")
        return normalized

    @staticmethod
    def _normalize_tenant_id(tenant_id: str) -> str:
        if not isinstance(tenant_id, str):
            raise ValueError("tenant_id must be a non-empty string")
        normalized = tenant_id.strip()
        if not normalized:
            raise ValueError("tenant_id must be a non-empty string")
        return normalized

    # ------------------------------------------------------------------
    # Task 2.4 — trigger registration
    # ------------------------------------------------------------------

    def register(
        self,
        event_name: str,
        expression: str,
        focus: str | None = None,
        fallback_handler: Callable | None = None,
        **kwargs: Any,
    ) -> None:
        """Register a cron trigger.

        Args:
            event_name: Unique event identifier.
            expression: 5-field cron expression (e.g. ``"0 * * * *"``).
            focus: Optional focus tag to narrow Agent skill loading.
            fallback_handler: Callable invoked when fallback strategy fires.
            **kwargs: Additional CronTriggerConfig fields.

        Raises:
            ValueError: If *event_name* is already registered or *expression*
                is invalid.
        """
        event_name = self._normalize_event_name(event_name)
        if not isinstance(expression, str):
            raise ValueError("expression must be a non-empty string")
        expression = expression.strip()
        if not expression:
            raise ValueError("expression must not be empty")
        if isinstance(focus, str):
            focus = focus.strip() or None

        if event_name in self._triggers:
            raise ValueError(f"Cron trigger '{event_name}' is already registered")

        if not self._validate_cron_expression(expression):
            raise ValueError(f"Invalid cron expression: '{expression}'")

        migration_weight = kwargs.get("migration_weight", 1.0)
        if (
            isinstance(migration_weight, bool)
            or not isinstance(migration_weight, int | float | Decimal)
            or migration_weight < 0.0
            or migration_weight > 1.0
        ):
            raise ValueError("migration_weight must be a float between 0.0 and 1.0")
        kwargs["migration_weight"] = float(migration_weight)

        config = CronTriggerConfig(
            event_name=event_name,
            expression=expression,
            focus=focus,
            fallback_handler=fallback_handler,
            **kwargs,
        )
        self._triggers[event_name] = config

        logger.info(
            "Registered cron trigger event_name=%s expression=%s focus=%s",
            event_name,
            expression,
            focus,
        )

    # ------------------------------------------------------------------
    # Task 2.5 — query methods
    # ------------------------------------------------------------------

    def get_trigger(self, event_name: str) -> CronTriggerConfig | None:
        """Return the CronTriggerConfig for *event_name*, or None if missing."""
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            return None
        return self._triggers.get(event_name)

    def list_triggers(self) -> list[CronTriggerConfig]:
        """Return all registered trigger configurations."""
        return list(self._triggers.values())

    def _record_recent_execution(
        self,
        event_name: str,
        status: str,
        duration_seconds: float | None,
    ) -> None:
        """Store lightweight recent execution stats for status reporting."""
        key = event_name.strip()
        if not key:
            return
        bucket = self._recent_executions.setdefault(key, deque(maxlen=50))
        bucket.append((status, duration_seconds))

    # ------------------------------------------------------------------
    # Management helpers (Task 8 pause/resume)
    # ------------------------------------------------------------------

    def get_all(self) -> dict[str, CronTriggerConfig]:
        """Return a shallow copy of the internal triggers dict."""
        return dict(self._triggers)

    def pause_trigger(self, event_name: str) -> None:
        """Disable a trigger so future cron fires are skipped.

        Raises:
            KeyError: If *event_name* is not registered.
        """
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            raise KeyError("Cron trigger '' not found") from None
        config = self._triggers.get(event_name)
        if config is None:
            raise KeyError(f"Cron trigger '{event_name}' not found")
        config.enabled = False
        logger.info("Paused cron trigger: %s", event_name)

    def resume_trigger(self, event_name: str) -> None:
        """Re-enable a previously paused trigger.

        Raises:
            KeyError: If *event_name* is not registered.
        """
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            raise KeyError("Cron trigger '' not found") from None
        config = self._triggers.get(event_name)
        if config is None:
            raise KeyError(f"Cron trigger '{event_name}' not found")
        config.enabled = True
        logger.info("Resumed cron trigger: %s", event_name)

    async def trigger_now(
        self,
        event_name: str,
        **kwargs: Any,
    ) -> str:
        """Trigger an immediate run of the cron workflow (manual trigger).

        Calls Hatchet to run the task now without waiting for the cron schedule.
        Must be called after start().

        Args:
            event_name: The registered trigger event name.
            **kwargs: Optional context passed to the run (e.g. focus override).

        Returns:
            Workflow run id from Hatchet.

        Raises:
            KeyError: If *event_name* is not registered.
            RuntimeError: If start() has not been called (no Hatchet client).
        """
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            raise KeyError("Cron trigger '' not found") from None
        if event_name not in self._triggers:
            raise KeyError(f"Cron trigger '{event_name}' not found")
        if self._hatchet_client is None:
            raise RuntimeError(
                "trigger_now requires start() to be called with a Hatchet client"
            )
        run_task_now = getattr(self._hatchet_client, "run_task_now", None)
        if not callable(run_task_now):
            raise RuntimeError(
                "trigger_now requires Hatchet client with run_task_now() support"
            )
        task_name = f"cron_{event_name}"
        if "tenant_id" not in kwargs:
            kwargs["tenant_id"] = self._tenant_id
        else:
            kwargs["tenant_id"] = self._normalize_tenant_id(kwargs["tenant_id"])
        run_id = await run_task_now(task_name, **kwargs)
        self._record_recent_execution(event_name, "success", 0.0)
        if self._ledger is not None:
            try:
                await self._ledger.record_execution(
                    tenant_id=kwargs["tenant_id"],
                    agent_id=(self.app.name if self.app else "") or event_name,
                    run_id=str(run_id),
                    capability_name=event_name,
                    task_type="cron_manual_trigger",
                    input_params={"trigger_type": "manual", "kwargs": dict(kwargs)},
                    output_result={"run_id": str(run_id)},
                    decision_reasoning="manual_trigger",
                    execution_time_ms=0,
                    llm_model="",
                    llm_tokens_input=0,
                    llm_tokens_output=0,
                    estimated_cost=Decimal("0"),
                    status="success",
                    error_message=None,
                )
            except Exception as exc:
                logger.exception("Failed to record manual trigger for '%s': %s", event_name, exc)
        return str(run_id)

    async def get_execution_history(
        self,
        event_name: str,
        limit: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return execution history for a trigger from Ledger.

        Queries Ledger for cron_execution records with capability_name=event_name.
        Must be called after start() with a Ledger.

        Args:
            event_name: The registered trigger event name.
            limit: Max number of records to return (default 10).
            tenant_id: Override tenant; defaults to tenant from start().

        Returns:
            List of execution records (run_id, status, created_at, etc.).

        Raises:
            KeyError: If *event_name* is not registered.
            RuntimeError: If Ledger was not provided to start().
        """
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            raise KeyError("Cron trigger '' not found") from None
        if event_name not in self._triggers:
            raise KeyError(f"Cron trigger '{event_name}' not found")
        if self._ledger is None:
            raise RuntimeError(
                "get_execution_history requires start() to be called with a Ledger"
            )
        from owlclaw.governance.ledger import LedgerQueryFilters

        if isinstance(limit, bool):
            safe_limit = 10
        else:
            try:
                safe_limit = int(limit)
            except (TypeError, ValueError):
                safe_limit = 10
        safe_limit = max(1, min(safe_limit, 100))

        tid = self._tenant_id if tenant_id is None else self._normalize_tenant_id(tenant_id)
        filters = LedgerQueryFilters(
            capability_name=event_name,
            limit=safe_limit,
            order_by="created_at DESC",
        )
        records = await self._ledger.query_records(tenant_id=tid, filters=filters)
        out: list[dict[str, Any]] = []
        for r in records:
            out.append({
                "run_id": r.run_id,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "execution_time_ms": r.execution_time_ms,
                "agent_run_id": (r.output_result or {}).get("agent_run_id"),
                "error_message": r.error_message,
            })
        return out

    def get_trigger_status(self, event_name: str) -> dict[str, Any]:
        """Return status for a trigger: config, enabled, next run time.

        Args:
            event_name: The registered trigger event name.

        Returns:
            Dict with event_name, enabled, expression, focus, next_run (ISO datetime).

        Raises:
            KeyError: If *event_name* is not registered.
        """
        try:
            event_name = self._normalize_event_name(event_name)
        except ValueError:
            raise KeyError("Cron trigger '' not found") from None
        config = self._triggers.get(event_name)
        if config is None:
            raise KeyError(f"Cron trigger '{event_name}' not found")
        next_run: str | None = None
        try:
            it = croniter(config.expression, datetime.now(timezone.utc))
            next_dt = it.get_next(datetime)
            next_run = next_dt.isoformat() if next_dt else None
        except Exception as exc:
            logger.warning(
                "Failed to compute next cron run event_name=%s expression=%s: %s",
                event_name,
                config.expression,
                exc,
            )
        samples = list(self._recent_executions.get(event_name, ()))
        sample_size = len(samples)
        success_statuses = {"success", "fallback"}
        success_count = sum(1 for status, _ in samples if status in success_statuses)
        durations = [value for _, value in samples if isinstance(value, int | float) and value >= 0]
        success_rate = (success_count / sample_size) if sample_size > 0 else None
        avg_duration = (sum(durations) / len(durations)) if durations else None

        return {
            "event_name": event_name,
            "enabled": config.enabled,
            "expression": config.expression,
            "focus": config.focus,
            "next_run": next_run,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "sample_size": sample_size,
        }

    # ------------------------------------------------------------------
    # Task 3.1 — Hatchet registration
    # ------------------------------------------------------------------

    def start(
        self,
        hatchet_client: HatchetClient,
        *,
        agent_runtime: AgentRuntime | None = None,
        ledger: Ledger | None = None,
        tenant_id: str = "default",
    ) -> None:
        """Register all stored triggers as Hatchet cron tasks.

        Must be called after *hatchet_client* is connected (i.e. after
        ``HatchetClient.connect()``).  Each trigger is wrapped in a closure
        that captures *config*, *agent_runtime*, *ledger*, and *tenant_id*.

        Args:
            hatchet_client: Connected :class:`HatchetClient` instance.
            agent_runtime: Optional :class:`AgentRuntime`; if omitted, all
                runs fall back to the configured fallback handler.
            ledger: Optional :class:`Ledger` for execution recording and
                governance constraint queries.
            tenant_id: Multi-tenancy identifier forwarded to runs.
        """
        tenant_id = self._normalize_tenant_id(tenant_id)
        self._hatchet_client = hatchet_client
        self._ledger = ledger
        self._tenant_id = tenant_id
        for config in self._triggers.values():
            self._register_hatchet_task(
                hatchet_client, config, agent_runtime, ledger, tenant_id
            )
        if agent_runtime is not None:
            self._register_agent_scheduled_run(hatchet_client, agent_runtime, tenant_id)
        logger.info(
            "Registered %d cron triggers with Hatchet", len(self._triggers)
        )

    def _register_hatchet_task(
        self,
        hatchet_client: HatchetClient,
        config: CronTriggerConfig,
        agent_runtime: AgentRuntime | None,
        ledger: Ledger | None,
        tenant_id: str,
    ) -> None:
        """Create the Hatchet task function for a single trigger."""
        registry = self

        async def cron_handler(_ctx: Any) -> dict[str, Any]:
            return await registry._run_cron(
                config, agent_runtime, ledger, tenant_id
            )

        cron_handler.__name__ = f"cron_{config.event_name}"
        # Apply the Hatchet task decorator
        hatchet_client.task(
            name=f"cron_{config.event_name}",
            cron=config.expression,
            retries=config.max_retries if config.retry_on_failure else 0,
            priority=config.priority or 1,
        )(cron_handler)
        self._hatchet_workflows[config.event_name] = cron_handler

    def _register_agent_scheduled_run(
        self,
        hatchet_client: HatchetClient,
        agent_runtime: AgentRuntime,
        tenant_id: str,
    ) -> None:
        """Register agent_scheduled_run task for schedule_once built-in tool."""

        async def agent_scheduled_run_handler(inp: Any, _ctx: Any) -> dict[str, Any]:
            data = inp if isinstance(inp, dict) else {}
            focus = data.get("focus", "")
            payload = {**data, "tenant_id": data.get("tenant_id", tenant_id)}
            result = await agent_runtime.trigger_event(
                "scheduled_run",
                focus=focus or None,
                payload=payload,
                tenant_id=payload.get("tenant_id", tenant_id),
            )
            return {"status": "success", "run_id": result.get("run_id")}

        agent_scheduled_run_handler.__name__ = "agent_scheduled_run"
        hatchet_client.task(
            name="agent_scheduled_run",
            retries=1,
        )(agent_scheduled_run_handler)
        self._hatchet_workflows["agent_scheduled_run"] = agent_scheduled_run_handler

    # ------------------------------------------------------------------
    # Task 3.2 — Main execution step
    # ------------------------------------------------------------------

    async def _run_cron(
        self,
        config: CronTriggerConfig,
        agent_runtime: AgentRuntime | None,
        ledger: Ledger | None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Execute a single cron trigger run (called by the Hatchet step)."""
        execution = CronExecution(
            execution_id=str(uuid.uuid4()),
            event_name=config.event_name,
            triggered_at=datetime.now(timezone.utc),
            status=ExecutionStatus.PENDING,
            context={
                "trigger_type": "cron",
                "expression": config.expression,
                "focus": config.focus,
            },
        )

        try:
            # Skip if disabled
            if not config.enabled:
                execution.status = ExecutionStatus.SKIPPED
                execution.skip_reason = "trigger disabled"
                return {"status": execution.status.value, "reason": execution.skip_reason}

            # Task 3.3 — governance checks
            passed, reason = await self._check_governance(
                config, execution, ledger, tenant_id
            )
            if not passed:
                execution.status = ExecutionStatus.SKIPPED
                execution.skip_reason = reason
                return {"status": execution.status.value, "reason": reason}

            # Task 3.4 — Agent vs Fallback decision
            use_agent = self._should_use_agent(config)
            execution.decision_mode = "agent" if use_agent else "fallback"
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)

            if use_agent and agent_runtime is not None:
                # Task 3.5 — Agent path
                await self._execute_agent(config, execution, agent_runtime)
            else:
                # Task 3.6 — Fallback path
                await self._execute_fallback(config, execution)

            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.SUCCESS

        except Exception as exc:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(exc)
            execution.error_traceback = _traceback.format_exc()
            # Task 3.7 — failure handling
            await self._handle_failure(config, execution)

        finally:
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at is not None:
                execution.duration_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
            self._record_recent_execution(
                config.event_name,
                execution.status.value,
                execution.duration_seconds,
            )
            # Record run-level limit violations for auditing (config fields exist but are not pre-run enforced)
            if config.max_cost_per_run is not None and (execution.cost_usd or 0) > config.max_cost_per_run:
                execution.governance_checks["max_cost_per_run_exceeded"] = True
            if config.max_duration is not None and (execution.duration_seconds or 0) > config.max_duration:
                execution.governance_checks["max_duration_exceeded"] = True
            if ledger is not None:
                agent_id = (self.app.name if self.app else None) or config.event_name
                await self._record_to_ledger(
                    ledger, config, execution, tenant_id, agent_id=agent_id
                )

        return {
            "status": execution.status.value,
            "execution_id": execution.execution_id,
            "duration_seconds": execution.duration_seconds,
        }

    # ------------------------------------------------------------------
    # Task 3.3 — Governance checks
    # ------------------------------------------------------------------

    async def _check_governance(
        self,
        config: CronTriggerConfig,
        execution: CronExecution,
        ledger: Ledger | None,
        tenant_id: str,
    ) -> tuple[bool, str]:
        """Check governance constraints; return (passed, reason).

        Enforces: cooldown_seconds, max_daily_runs, max_daily_cost.
        max_cost_per_run and max_duration are not enforced here (run-level
        limits); violations are recorded in governance_checks after the run.
        Without a Ledger, time-based constraints are skipped (fail-open).
        """
        from owlclaw.governance.ledger import LedgerQueryFilters

        checks: dict[str, Any] = {}
        triggered_at = execution.triggered_at
        if triggered_at.tzinfo is None:
            triggered_at = triggered_at.replace(tzinfo=timezone.utc)
        execution_day = triggered_at.astimezone(timezone.utc).date()

        if ledger is not None and config.cooldown_seconds > 0:
            records = await ledger.query_records(
                tenant_id,
                LedgerQueryFilters(
                    capability_name=config.event_name,
                    order_by="created_at DESC",
                    limit=1,
                ),
            )
            if records:
                last = records[0]
                last_dt = last.created_at
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (
                    datetime.now(timezone.utc) - last_dt
                ).total_seconds()
                if elapsed < config.cooldown_seconds:
                    checks["cooldown"] = False
                    execution.governance_checks = checks
                    return (
                        False,
                        f"Cooldown not satisfied: {elapsed:.1f}s < {config.cooldown_seconds}s",
                    )
            checks["cooldown"] = True

        if ledger is not None and config.max_daily_runs is not None:
            records = await ledger.query_records(
                tenant_id,
                LedgerQueryFilters(
                    capability_name=config.event_name,
                    start_date=execution_day,
                    end_date=execution_day,
                ),
            )
            today_runs = len(records)
            if today_runs >= config.max_daily_runs:
                checks["daily_runs"] = False
                execution.governance_checks = checks
                return (
                    False,
                    f"Daily run limit reached: {today_runs} >= {config.max_daily_runs}",
                )
            checks["daily_runs"] = True

        if ledger is not None and config.max_daily_cost is not None:
            records = await ledger.query_records(
                tenant_id,
                LedgerQueryFilters(
                    capability_name=config.event_name,
                    start_date=execution_day,
                    end_date=execution_day,
                ),
            )
            today_cost = sum(
                float(r.estimated_cost or 0) for r in records
            )
            if today_cost >= config.max_daily_cost:
                checks["daily_cost"] = False
                execution.governance_checks = checks
                return (
                    False,
                    f"Daily cost limit reached: ${today_cost:.4f} >= ${config.max_daily_cost}",
                )
            checks["daily_cost"] = True

        execution.governance_checks = checks
        return True, ""

    # ------------------------------------------------------------------
    # Task 3.4 — Agent vs Fallback decision
    # ------------------------------------------------------------------

    @staticmethod
    def _should_use_agent(config: CronTriggerConfig) -> bool:
        """Return True if this run should use the Agent path.

        Uses ``migration_weight`` (0.0 → always fallback, 1.0 → always Agent).
        """
        return random.random() < config.migration_weight

    # ------------------------------------------------------------------
    # Task 3.5 — Agent execution path
    # ------------------------------------------------------------------

    async def _execute_agent(
        self,
        config: CronTriggerConfig,
        execution: CronExecution,
        agent_runtime: AgentRuntime,
    ) -> None:
        """Invoke agent_runtime.trigger_event and update execution record."""
        result = await agent_runtime.trigger_event(
            config.event_name,
            focus=config.focus,
            payload=execution.context,
        )
        if not isinstance(result, dict):
            raise RuntimeError("agent_runtime.trigger_event must return a dictionary")
        run_id = result.get("run_id")
        execution.agent_run_id = run_id.strip() if isinstance(run_id, str) and run_id.strip() else None
        raw_calls = result.get("tool_calls_total", 0)
        if isinstance(raw_calls, bool):
            execution.llm_calls = 0
        else:
            try:
                execution.llm_calls = max(0, int(raw_calls))
            except (TypeError, ValueError):
                execution.llm_calls = 0
        # Cost tracking requires Langfuse / litellm usage callback (future)

    # ------------------------------------------------------------------
    # Task 3.6 — Fallback execution path
    # ------------------------------------------------------------------

    async def _execute_fallback(
        self,
        config: CronTriggerConfig,
        execution: CronExecution,
    ) -> None:
        """Invoke the configured fallback handler (if any)."""
        if config.fallback_handler is None:
            logger.warning(
                "No fallback handler for '%s'; skipping fallback",
                config.event_name,
            )
            execution.status = ExecutionStatus.SKIPPED
            execution.skip_reason = "no fallback handler"
            return

        execution.decision_mode = "fallback"
        result = config.fallback_handler()
        if inspect.isawaitable(result):
            await result
        execution.status = ExecutionStatus.FALLBACK

    # ------------------------------------------------------------------
    # Task 3.7 — Failure handling
    # ------------------------------------------------------------------

    async def _handle_failure(
        self,
        config: CronTriggerConfig,
        execution: CronExecution,
    ) -> None:
        """Apply fallback_strategy on failure."""
        if config.fallback_strategy == "never":
            return
        if config.fallback_strategy in ("on_failure", "always"):
            try:
                await self._execute_fallback(config, execution)
            except Exception as fb_exc:
                logger.exception(
                    "Fallback handler also failed for '%s': %s",
                    config.event_name,
                    fb_exc,
                )

    # ------------------------------------------------------------------
    # Ledger recording helper
    # ------------------------------------------------------------------

    async def _record_to_ledger(
        self,
        ledger: Ledger,
        config: CronTriggerConfig,
        execution: CronExecution,
        tenant_id: str,
        *,
        agent_id: str,
    ) -> None:
        """Enqueue execution record to the Ledger (non-blocking).

        Uses app-level *agent_id* (e.g. OwlClaw app name) for cost and
        governance queries; run_id remains execution_id for traceability.
        """
        duration_ms = int((execution.duration_seconds or 0) * 1000)
        try:
            await ledger.record_execution(
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=execution.execution_id,
                capability_name=config.event_name,
                task_type="cron_execution",
                input_params=execution.context,
                output_result={"agent_run_id": execution.agent_run_id},
                decision_reasoning=execution.skip_reason,
                execution_time_ms=duration_ms,
                llm_model="",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal(str(execution.cost_usd)),
                status=execution.status.value,
                error_message=execution.error_message,
            )
        except Exception as exc:
            logger.exception(
                "Failed to record execution for '%s': %s", config.event_name, exc
            )
