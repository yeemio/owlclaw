"""Built-in tools available to all Agents via LLM function calling.

Tools: query_state, log_decision, schedule_once, schedule_cron, cancel_schedule.
remember/recall require Memory integration (see agent-tools spec).
"""

from __future__ import annotations

import asyncio
import logging
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


@dataclass
class BuiltInToolsContext:
    """Context passed to BuiltInTools.execute()."""

    agent_id: str
    run_id: str
    tenant_id: str = "default"


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
        self._scheduled_run_task = scheduled_run_task_name
        self._timeout = timeout_seconds

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
        return tool_name in _BUILTIN_TOOL_NAMES

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
        if tool_name not in _BUILTIN_TOOL_NAMES:
            raise ValueError(f"Unknown built-in tool: {tool_name}")
        if not isinstance(arguments, dict):
            return {
                "error": (
                    f"Invalid arguments for built-in tool '{tool_name}': "
                    "arguments must be a JSON object"
                )
            }

        if tool_name == "query_state":
            return await self._query_state(arguments, context)
        if tool_name == "log_decision":
            return await self._log_decision(arguments, context)
        if tool_name == "schedule_once":
            return await self._schedule_once(arguments, context)
        if tool_name == "schedule_cron":
            return await self._schedule_cron(arguments, context)
        if tool_name == "cancel_schedule":
            return await self._cancel_schedule(arguments, context)
        raise ValueError(f"Unknown built-in tool: {tool_name}")

    async def _query_state(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        state_name = arguments.get("state_name")
        if not state_name or not isinstance(state_name, str):
            return {"error": "state_name is required and must be a non-empty string"}

        if self._registry is None:
            return {"error": "No capability registry configured; query_state unavailable"}

        try:
            result = await asyncio.wait_for(
                self._registry.get_state(state_name),
                timeout=self._timeout,
            )
            return {"state": result}
        except asyncio.TimeoutError:
            return {"error": f"query_state timed out after {self._timeout}s"}
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.exception("query_state failed for %s", state_name)
            return {"error": str(e)}

    async def _log_decision(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        reasoning = arguments.get("reasoning")
        if not reasoning or not isinstance(reasoning, str):
            return {"error": "reasoning is required and must be a non-empty string"}
        if len(reasoning) > 1000:
            return {"error": "reasoning must not exceed 1000 characters"}

        decision_type = arguments.get("decision_type", "other")
        if decision_type not in ("capability_selection", "schedule_decision", "no_action", "other"):
            decision_type = "other"

        if self._ledger is None:
            return {"decision_id": "no-ledger", "logged": False}

        try:
            await self._ledger.record_execution(
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                run_id=context.run_id,
                capability_name="log_decision",
                task_type="builtin",
                input_params={"reasoning": reasoning, "decision_type": decision_type},
                output_result={"logged": True},
                decision_reasoning=reasoning,
                execution_time_ms=0,
                llm_model="builtin",
                llm_tokens_input=0,
                llm_tokens_output=0,
                estimated_cost=Decimal("0"),
                status="success",
            )
            return {"decision_id": context.run_id, "logged": True}
        except Exception as e:
            logger.exception("log_decision failed")
            return {"error": str(e), "logged": False}

    async def _schedule_once(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        delay = arguments.get("delay_seconds")
        focus = arguments.get("focus")
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 1 or delay > 2592000:
            return {
                "error": "delay_seconds must be an integer between 1 and 2592000",
            }
        if not focus or not isinstance(focus, str):
            return {"error": "focus is required and must be a non-empty string"}
        if self._hatchet is None:
            return {"error": "Hatchet not configured; schedule_once unavailable"}
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
            return {
                "schedule_id": schedule_id,
                "scheduled_at": f"in {delay} seconds",
                "focus": focus,
            }
        except asyncio.TimeoutError:
            return {"error": f"schedule_once timed out after {self._timeout}s"}
        except Exception as e:
            logger.exception("schedule_once failed")
            return {"error": str(e)}

    def _validate_cron_expression(self, expr: str) -> bool:
        """Validate cron expression (5 fields)."""
        return CronTriggerRegistry._validate_cron_expression(expr)

    async def _schedule_cron(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        cron_expr = arguments.get("cron_expression")
        focus = arguments.get("focus")
        if not cron_expr or not isinstance(cron_expr, str):
            return {"error": "cron_expression is required and must be a non-empty string"}
        if not focus or not isinstance(focus, str):
            return {"error": "focus is required and must be a non-empty string"}
        if not self._validate_cron_expression(cron_expr):
            return {"error": f"Invalid cron expression: {cron_expr!r}"}
        if self._hatchet is None:
            return {"error": "Hatchet not configured; schedule_cron unavailable"}
        cron_name = f"agent_cron_{context.agent_id}_{uuid.uuid4().hex[:12]}"
        input_data = {
            "agent_id": context.agent_id,
            "trigger": "schedule_cron",
            "focus": focus,
            "scheduled_by_run_id": context.run_id,
            "tenant_id": context.tenant_id,
        }
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
            return {
                "schedule_id": schedule_id,
                "cron_expression": cron_expr,
                "focus": focus,
            }
        except asyncio.TimeoutError:
            return {"error": f"schedule_cron timed out after {self._timeout}s"}
        except Exception as e:
            logger.exception("schedule_cron failed")
            return {"error": str(e)}

    async def _cancel_schedule(
        self,
        arguments: dict[str, Any],
        context: BuiltInToolsContext,
    ) -> dict[str, Any]:
        schedule_id = arguments.get("schedule_id")
        if not schedule_id or not isinstance(schedule_id, str):
            return {"error": "schedule_id is required and must be a non-empty string"}
        if self._hatchet is None:
            return {"error": "Hatchet not configured; cancel_schedule unavailable"}
        try:
            ok = await asyncio.wait_for(
                self._hatchet.cancel_task(schedule_id),
                timeout=self._timeout,
            )
            if not ok and hasattr(self._hatchet, "cancel_cron"):
                ok = await self._hatchet.cancel_cron(schedule_id)
            return {"cancelled": ok, "schedule_id": schedule_id}
        except asyncio.TimeoutError:
            return {"error": f"cancel_schedule timed out after {self._timeout}s"}
        except Exception as e:
            logger.exception("cancel_schedule failed")
            return {"error": str(e)}
