"""Built-in tools available to all Agents via LLM function calling.

Tools: query_state, log_decision, schedule_once, schedule_cron, cancel_schedule.
remember/recall require Memory integration (see agent-tools spec).
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from owlclaw.triggers.cron import CronTriggerRegistry

if TYPE_CHECKING:
    from owlclaw.capabilities.registry import CapabilityRegistry
    from owlclaw.governance.ledger import Ledger
    from owlclaw.integrations.hatchet import HatchetClient

logger = logging.getLogger(__name__)

_SCHEDULED_RUN_TASK = "agent_scheduled_run"
_BUILTIN_TOOL_NAMES = frozenset(
    {"query_state", "log_decision", "schedule_once", "schedule_cron", "cancel_schedule"}
)
_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass
class BuiltInToolsContext:
    """Context passed to BuiltInTools.execute()."""

    agent_id: str
    run_id: str
    tenant_id: str = "default"

    def __post_init__(self) -> None:
        for field_name in ("agent_id", "run_id", "tenant_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            setattr(self, field_name, value.strip())


def _query_state_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "query_state",
            "description": "Query the current state from a registered state provider. Use this to get business context (e.g. market_state, portfolio_snapshot) before making decisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state_name": {
                        "type": "string",
                        "description": "Name of the state to query (must be registered via @app.state)",
                    },
                },
                "required": ["state_name"],
            },
        },
    }


def _log_decision_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "log_decision",
            "description": "Record a decision and reasoning to the audit ledger. Use when you choose no_action, defer, or want to document your reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of the decision (max 1000 chars)",
                    },
                    "decision_type": {
                        "type": "string",
                        "enum": ["capability_selection", "schedule_decision", "no_action", "other"],
                        "description": "Type of decision",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }


def _schedule_once_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "schedule_once",
            "description": (
                "Schedule a one-time delayed Agent run. "
                "Use when you need to check something later or wait for an event."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": "Delay in seconds (1–2592000, max 30 days)",
                        "minimum": 1,
                        "maximum": 2592000,
                    },
                    "focus": {
                        "type": "string",
                        "description": "What to focus on in the next run (e.g. 'check entry opportunities')",
                    },
                },
                "required": ["delay_seconds", "focus"],
            },
        },
    }


def _schedule_cron_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "schedule_cron",
            "description": (
                "Schedule a recurring Agent run using a cron expression. "
                "Use for periodic checks (e.g. every hour during trading hours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cron_expression": {
                        "type": "string",
                        "description": (
                            "Cron expression (minute hour day month weekday), "
                            "e.g. '0 9 * * 1-5' for 9am on weekdays"
                        ),
                    },
                    "focus": {
                        "type": "string",
                        "description": "What to focus on in each run",
                    },
                },
                "required": ["cron_expression", "focus"],
            },
        },
    }


def _cancel_schedule_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "cancel_schedule",
            "description": "Cancel a scheduled run by schedule_id (from schedule_once or schedule_cron).",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "The ID returned by schedule_once",
                    },
                },
                "required": ["schedule_id"],
            },
        },
    }


class BuiltInTools:
    """Built-in tools: query_state, log_decision, schedule_once, cancel_schedule.

    Optional dependencies: capability_registry (query_state), ledger (log_decision),
    hatchet_client (schedule_once, cancel_schedule). If a dependency is None,
    the corresponding tool returns an error message.
    """

    def __init__(
        self,
        *,
        capability_registry: CapabilityRegistry | None = None,
        ledger: Ledger | None = None,
        hatchet_client: HatchetClient | None = None,
        scheduled_run_task_name: str = _SCHEDULED_RUN_TASK,
        timeout_seconds: float = 30,
    ) -> None:
        self._registry = capability_registry
        self._ledger = ledger
        self._hatchet = hatchet_client
        task_name = self._non_empty_str(scheduled_run_task_name)
        if task_name is None:
            raise ValueError("scheduled_run_task_name must be a non-empty string")
        self._scheduled_run_task = task_name
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a positive finite number")
        timeout_val = float(timeout_seconds)
        if not math.isfinite(timeout_val) or timeout_val <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        self._timeout = timeout_val

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-style function schemas for all built-in tools."""
        schemas = [
            _query_state_schema(),
            _log_decision_schema(),
            _schedule_once_schema(),
            _schedule_cron_schema(),
            _cancel_schedule_schema(),
        ]
        return schemas

    def is_builtin(self, tool_name: str) -> bool:
        """Return True if *tool_name* is a built-in tool."""
        if not isinstance(tool_name, str):
            return False
        return tool_name.strip() in _BUILTIN_TOOL_NAMES

    @staticmethod
    def _non_empty_str(value: Any) -> str | None:
        """Return trimmed non-empty string, else None."""
        if not isinstance(value, str):
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = _SAFE_NAME_PATTERN.sub("_", value.strip())
        normalized = normalized.strip("_")
        return normalized or "agent"

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> Any:
        """Execute a built-in tool by name.

        Raises:
            ValueError: If tool_name is not a built-in tool.
        """
        normalized_tool_name = tool_name.strip() if isinstance(tool_name, str) else ""
        if normalized_tool_name not in _BUILTIN_TOOL_NAMES:
            raise ValueError(f"Unknown built-in tool: {tool_name}")
        if not isinstance(arguments, dict):
            error = (
                f"Invalid arguments for built-in tool '{normalized_tool_name}': "
                "arguments must be a JSON object"
            )
            out = {
                "error": (
                    error
                )
            }
            await self._record_validation_failure(
                tool_name=normalized_tool_name,
                context=context,
                input_params={"arguments_type": type(arguments).__name__},
                error_message=error,
            )
            return out

        if normalized_tool_name == "query_state":
            return await self._query_state(arguments, context)
        if normalized_tool_name == "log_decision":
            return await self._log_decision(arguments, context)
        if normalized_tool_name == "schedule_once":
            return await self._schedule_once(arguments, context)
        if normalized_tool_name == "schedule_cron":
            return await self._schedule_cron(arguments, context)
        if normalized_tool_name == "cancel_schedule":
            return await self._cancel_schedule(arguments, context)
        raise ValueError(f"Unknown built-in tool: {normalized_tool_name}")

    async def _query_state(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        state_name = self._non_empty_str(arguments.get("state_name"))
        if state_name is None:
            error = "state_name is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="query_state",
                context=context,
                input_params={"state_name": arguments.get("state_name")},
                error_message=error,
            )
            return {"error": error}

        if self._registry is None:
            error = "No capability registry configured; query_state unavailable"
            await self._record_validation_failure(
                tool_name="query_state",
                context=context,
                input_params={"state_name": state_name},
                error_message=error,
            )
            return {"error": error}

        start_ns = time.perf_counter_ns()
        try:
            result = await asyncio.wait_for(
                self._registry.get_state(state_name),
                timeout=self._timeout,
            )
            out = {"state": result}
            await self._record_tool_execution(
                tool_name="query_state",
                context=context,
                input_params={"state_name": state_name},
                output_result=out,
                start_ns=start_ns,
                status="success",
                error_message=None,
            )
            return out
        except asyncio.TimeoutError:
            error = f"query_state timed out after {self._timeout}s"
            await self._record_tool_execution(
                tool_name="query_state",
                context=context,
                input_params={"state_name": state_name},
                output_result=None,
                start_ns=start_ns,
                status="timeout",
                error_message=error,
            )
            return {"error": error}
        except ValueError as e:
            await self._record_tool_execution(
                tool_name="query_state",
                context=context,
                input_params={"state_name": state_name},
                output_result=None,
                start_ns=start_ns,
                status="error",
                error_message=str(e),
            )
            return {"error": str(e)}
        except Exception as e:
            logger.exception("query_state failed for %s", state_name)
            await self._record_tool_execution(
                tool_name="query_state",
                context=context,
                input_params={"state_name": state_name},
                output_result=None,
                start_ns=start_ns,
                status="error",
                error_message=str(e),
            )
            return {"error": str(e)}

    async def _log_decision(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        reasoning = self._non_empty_str(arguments.get("reasoning"))
        if reasoning is None:
            error = "reasoning is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="log_decision",
                context=context,
                input_params={"reasoning": arguments.get("reasoning")},
                error_message=error,
            )
            return {"error": error}
        if len(reasoning) > 1000:
            error = "reasoning must not exceed 1000 characters"
            await self._record_validation_failure(
                tool_name="log_decision",
                context=context,
                input_params={"reasoning_length": len(reasoning)},
                error_message=error,
            )
            return {"error": error}

        decision_type = arguments.get("decision_type", "other")
        if decision_type not in ("capability_selection", "schedule_decision", "no_action", "other"):
            decision_type = "other"

        if self._ledger is None:
            return {"decision_id": "no-ledger", "logged": False}

        try:
            decision_id = f"decision-{uuid.uuid4().hex}"
            await self._ledger.record_execution(
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                run_id=context.run_id,
                capability_name="log_decision",
                task_type="decision_log",
                input_params={"reasoning": reasoning, "decision_type": decision_type},
                output_result={"logged": True, "decision_id": decision_id},
                decision_reasoning=reasoning,
                execution_time_ms=0,
                llm_model="builtin",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal("0"),
                status="success",
            )
            return {"decision_id": decision_id, "logged": True}
        except Exception as e:
            logger.exception("log_decision failed")
            return {"error": str(e), "logged": False}

    async def _schedule_once(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        delay = arguments.get("delay_seconds")
        focus = self._non_empty_str(arguments.get("focus"))
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 1 or delay > 2592000:
            error = "delay_seconds must be an integer between 1 and 2592000"
            await self._record_validation_failure(
                tool_name="schedule_once",
                context=context,
                input_params={"delay_seconds": delay},
                error_message=error,
            )
            return {"error": error}
        if focus is None:
            error = "focus is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="schedule_once",
                context=context,
                input_params={"focus": arguments.get("focus")},
                error_message=error,
            )
            return {"error": error}
        if self._hatchet is None:
            error = "Hatchet not configured; schedule_once unavailable"
            await self._record_validation_failure(
                tool_name="schedule_once",
                context=context,
                input_params={"delay_seconds": delay, "focus": focus},
                error_message=error,
            )
            return {"error": error}
        start_ns = time.perf_counter_ns()
        try:
            schedule_id = await asyncio.wait_for(
                self._hatchet.schedule_task(
                    self._scheduled_run_task,
                    delay,
                    agent_id=context.agent_id,
                    trigger="schedule_once",
                    focus=focus,
                    scheduled_by_run_id=context.run_id,
                    tenant_id=context.tenant_id,
                ),
                timeout=self._timeout,
            )
            out = {
                "schedule_id": schedule_id,
                "scheduled_at": f"in {delay} seconds",
                "focus": focus,
            }
            await self._record_tool_execution(
                tool_name="schedule_once",
                context=context,
                input_params={"delay_seconds": delay, "focus": focus},
                output_result=out,
                start_ns=start_ns,
                status="success",
                error_message=None,
            )
            return out
        except asyncio.TimeoutError:
            error = f"schedule_once timed out after {self._timeout}s"
            await self._record_tool_execution(
                tool_name="schedule_once",
                context=context,
                input_params={"delay_seconds": delay, "focus": focus},
                output_result=None,
                start_ns=start_ns,
                status="timeout",
                error_message=error,
            )
            return {"error": error}
        except Exception as e:
            logger.exception("schedule_once failed")
            await self._record_tool_execution(
                tool_name="schedule_once",
                context=context,
                input_params={"delay_seconds": delay, "focus": focus},
                output_result=None,
                start_ns=start_ns,
                status="error",
                error_message=str(e),
            )
            return {"error": str(e)}

    def _validate_cron_expression(self, expr: str) -> bool:
        """Validate cron expression (5 fields)."""
        return CronTriggerRegistry._validate_cron_expression(expr)

    async def _schedule_cron(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        cron_expr = self._non_empty_str(arguments.get("cron_expression"))
        focus = self._non_empty_str(arguments.get("focus"))
        if cron_expr is None:
            error = "cron_expression is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": arguments.get("cron_expression")},
                error_message=error,
            )
            return {"error": error}
        if focus is None:
            error = "focus is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="schedule_cron",
                context=context,
                input_params={"focus": arguments.get("focus")},
                error_message=error,
            )
            return {"error": error}
        if not self._validate_cron_expression(cron_expr):
            error = f"Invalid cron expression: {cron_expr!r}"
            await self._record_validation_failure(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": cron_expr, "focus": focus},
                error_message=error,
            )
            return {"error": error}
        if self._hatchet is None:
            error = "Hatchet not configured; schedule_cron unavailable"
            await self._record_validation_failure(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": cron_expr, "focus": focus},
                error_message=error,
            )
            return {"error": error}
        safe_agent_id = self._safe_name(context.agent_id)
        cron_name = f"agent_cron_{safe_agent_id}_{uuid.uuid4().hex[:12]}"
        input_data = {
            "agent_id": context.agent_id,
            "trigger": "schedule_cron",
            "focus": focus,
            "scheduled_by_run_id": context.run_id,
            "tenant_id": context.tenant_id,
        }
        start_ns = time.perf_counter_ns()
        try:
            schedule_id = await asyncio.wait_for(
                self._hatchet.schedule_cron(
                    workflow_name=self._scheduled_run_task,
                    cron_name=cron_name,
                    expression=cron_expr,
                    input_data=input_data,
                ),
                timeout=self._timeout,
            )
            out = {
                "schedule_id": schedule_id,
                "cron_name": cron_name,
                "cron_expression": cron_expr,
                "focus": focus,
            }
            await self._record_tool_execution(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": cron_expr, "focus": focus},
                output_result=out,
                start_ns=start_ns,
                status="success",
                error_message=None,
            )
            return out
        except asyncio.TimeoutError:
            error = f"schedule_cron timed out after {self._timeout}s"
            await self._record_tool_execution(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": cron_expr, "focus": focus},
                output_result=None,
                start_ns=start_ns,
                status="timeout",
                error_message=error,
            )
            return {"error": error}
        except Exception as e:
            logger.exception("schedule_cron failed")
            await self._record_tool_execution(
                tool_name="schedule_cron",
                context=context,
                input_params={"cron_expression": cron_expr, "focus": focus},
                output_result=None,
                start_ns=start_ns,
                status="error",
                error_message=str(e),
            )
            return {"error": str(e)}

    async def _cancel_schedule(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        schedule_id = self._non_empty_str(arguments.get("schedule_id"))
        if schedule_id is None:
            error = "schedule_id is required and must be a non-empty string"
            await self._record_validation_failure(
                tool_name="cancel_schedule",
                context=context,
                input_params={"schedule_id": arguments.get("schedule_id")},
                error_message=error,
            )
            return {"error": error}
        if self._hatchet is None:
            error = "Hatchet not configured; cancel_schedule unavailable"
            await self._record_validation_failure(
                tool_name="cancel_schedule",
                context=context,
                input_params={"schedule_id": schedule_id},
                error_message=error,
            )
            return {"error": error}
        start_ns = time.perf_counter_ns()
        try:
            ok = await asyncio.wait_for(
                self._hatchet.cancel_task(schedule_id),
                timeout=self._timeout,
            )
            if not ok and hasattr(self._hatchet, "cancel_cron"):
                ok = await asyncio.wait_for(
                    self._hatchet.cancel_cron(schedule_id),
                    timeout=self._timeout,
                )
            ok = bool(ok)
            out = {"cancelled": ok, "schedule_id": schedule_id}
            await self._record_tool_execution(
                tool_name="cancel_schedule",
                context=context,
                input_params={"schedule_id": schedule_id},
                output_result=out,
                start_ns=start_ns,
                status="success" if ok else "not_found",
                error_message=None if ok else "schedule not found",
            )
            return out
        except asyncio.TimeoutError:
            error = f"cancel_schedule timed out after {self._timeout}s"
            await self._record_tool_execution(
                tool_name="cancel_schedule",
                context=context,
                input_params={"schedule_id": schedule_id},
                output_result=None,
                start_ns=start_ns,
                status="timeout",
                error_message=error,
            )
            return {"error": error}
        except Exception as e:
            logger.exception("cancel_schedule failed")
            await self._record_tool_execution(
                tool_name="cancel_schedule",
                context=context,
                input_params={"schedule_id": schedule_id},
                output_result=None,
                start_ns=start_ns,
                status="error",
                error_message=str(e),
            )
            return {"error": str(e)}

    async def _record_tool_execution(
        self,
        *,
        tool_name: str,
        context: BuiltInToolsContext,
        input_params: dict[str, Any],
        output_result: dict[str, Any] | None,
        start_ns: int,
        status: str,
        error_message: str | None,
    ) -> None:
        """Best-effort audit record for built-in tool execution."""
        if self._ledger is None:
            return
        try:
            elapsed_ms = max(0, (time.perf_counter_ns() - start_ns) // 1_000_000)
            await self._ledger.record_execution(
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                run_id=context.run_id,
                capability_name=tool_name,
                task_type="builtin",
                input_params=input_params,
                output_result=output_result,
                decision_reasoning="builtin_tool_execution",
                execution_time_ms=elapsed_ms,
                llm_model="builtin",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal("0"),
                status=status,
                error_message=error_message,
            )
        except Exception:
            logger.exception("Failed to record built-in tool execution: %s", tool_name)

    async def _record_validation_failure(
        self,
        *,
        tool_name: str,
        context: BuiltInToolsContext,
        input_params: dict[str, Any],
        error_message: str,
    ) -> None:
        """Record validation/availability errors for built-in tools."""
        await self._record_tool_execution(
            tool_name=tool_name,
            context=context,
            input_params=input_params,
            output_result=None,
            start_ns=time.perf_counter_ns(),
            status="validation_error",
            error_message=error_message,
        )
