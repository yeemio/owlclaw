"""AgentRuntime — core orchestrator for Agent execution.

Responsibilities:
- Load Agent identity (SOUL.md, IDENTITY.md) via IdentityLoader
- Inject Skills knowledge into the system prompt
- Build the governance-filtered visible tools list
- Execute the LLM function-calling decision loop (via litellm)
- Provide trigger_event() as the public entry point for cron/webhook/etc.

This MVP implementation omits:
- Long-term memory (vector search) — returns empty; add later with MemorySystem
- Langfuse tracing — optional; add later with integrations-langfuse
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import math
import os
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.heartbeat import HeartbeatChecker
from owlclaw.agent.runtime.identity import IdentityLoader
from owlclaw.integrations import llm as llm_integration
from owlclaw.security.audit import SecurityAuditLog
from owlclaw.security.sanitizer import InputSanitizer

if TYPE_CHECKING:
    from owlclaw.agent.tools import BuiltInTools
    from owlclaw.capabilities.knowledge import KnowledgeInjector
    from owlclaw.capabilities.registry import CapabilityRegistry
    from owlclaw.governance.ledger import Ledger
    from owlclaw.governance.router import Router
    from owlclaw.governance.visibility import VisibilityFilter

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_ITERATIONS = 50
_DEFAULT_LLM_TIMEOUT_SECONDS = 60.0
_DEFAULT_RUN_TIMEOUT_SECONDS = 300.0


def _coerce_confirmation_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return False


def _normalize_risk_level(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"low", "medium", "high", "critical"}:
            return normalized
    return "low"


class AgentRuntime:
    """Core orchestrator for a single Agent.

    All constructor dependencies are optional so the runtime can be
    instantiated even before the full OwlClaw app is assembled; call
    :meth:`setup` before :meth:`run` or :meth:`trigger_event`.

    Args:
        agent_id: Stable name for this Agent (usually the OwlClaw app name).
        app_dir: Path to the application directory containing SOUL.md /
            IDENTITY.md and the capabilities folder.
        registry: Registered capability handlers and state providers.
        knowledge_injector: Formats Skills content for the system prompt.
        visibility_filter: Governance-layer capability filter; if *None* all
            registered capabilities are visible.
        router: Optional model router (task_type → model); if set, used before
            each LLM call instead of fixed *model*.
        ledger: Optional execution ledger; if set, capability runs are recorded.
        model: LLM model string (default when router is None or returns None).
        config: Optional runtime configuration overrides.
    """

    def __init__(
        self,
        agent_id: str,
        app_dir: str,
        *,
        registry: CapabilityRegistry | None = None,
        knowledge_injector: KnowledgeInjector | None = None,
        visibility_filter: VisibilityFilter | None = None,
        builtin_tools: BuiltInTools | None = None,
        router: Router | None = None,
        ledger: Ledger | None = None,
        model: str = _DEFAULT_MODEL,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        if not isinstance(app_dir, str) or not app_dir.strip():
            raise ValueError("app_dir must be a non-empty string")
        self.agent_id = agent_id.strip()
        self.app_dir = app_dir.strip()
        self.registry = registry
        self.knowledge_injector = knowledge_injector
        self.visibility_filter = visibility_filter
        self.builtin_tools = builtin_tools
        self._router = router
        self._ledger = ledger
        self.model = model
        self.config: dict[str, Any] = config or {}
        self._input_sanitizer = InputSanitizer()
        self._security_audit = SecurityAuditLog()

        self._identity_loader: IdentityLoader | None = None
        self._heartbeat_checker: HeartbeatChecker | None = None
        self._langfuse_init_error: str | None = None
        self._langfuse = self._init_langfuse_client()
        self.is_initialized = False

    def _init_langfuse_client(self) -> Any | None:
        """Initialize optional Langfuse client from runtime config."""
        cfg = self.config.get("langfuse")
        if not isinstance(cfg, dict):
            return None
        injected = cfg.get("client")
        if injected is not None:
            return injected
        if not cfg.get("enabled", False):
            return None

        public_key = cfg.get("public_key") or os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = cfg.get("secret_key") or os.environ.get("LANGFUSE_SECRET_KEY")
        host = cfg.get("host", "https://cloud.langfuse.com")
        if not public_key or not secret_key:
            return None
        try:
            module = importlib.import_module("langfuse")
            langfuse_cls = getattr(module, "Langfuse")
            try:
                return langfuse_cls(
                    public_key=public_key,
                    secret_key=secret_key,
                    base_url=host,
                )
            except TypeError:
                return langfuse_cls(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host,
                )
        except Exception as exc:
            self._langfuse_init_error = str(exc)
            logger.warning("Langfuse init failed: %s", exc)
            return None

    def _create_trace(self, context: AgentRunContext) -> Any | None:
        if self._langfuse is None:
            return None
        trace_fn = getattr(self._langfuse, "trace", None)
        if not callable(trace_fn):
            return None
        try:
            return trace_fn(
                name="agent_run",
                metadata={
                    "agent_id": context.agent_id,
                    "run_id": context.run_id,
                    "trigger": context.trigger,
                    "focus": context.focus,
                    "tenant_id": context.tenant_id,
                },
            )
        except Exception as exc:
            logger.warning("Langfuse trace create failed: %s", exc)
            return None

    @staticmethod
    def _update_trace(trace: Any | None, **kwargs: Any) -> None:
        if trace is None:
            return
        update_fn = getattr(trace, "update", None)
        if callable(update_fn):
            try:
                update_fn(**kwargs)
            except Exception:
                logger.debug("Langfuse trace update failed", exc_info=True)

    @staticmethod
    def _observe_tool(trace: Any | None, name: str, payload: dict[str, Any]) -> Any | None:
        if trace is None:
            return None
        span_fn = getattr(trace, "span", None)
        if callable(span_fn):
            try:
                return span_fn(name=name, input=payload)
            except Exception:
                logger.debug("Langfuse span create failed", exc_info=True)
        event_fn = getattr(trace, "event", None)
        if callable(event_fn):
            try:
                return event_fn(name=name, input=payload)
            except Exception:
                logger.debug("Langfuse event create failed", exc_info=True)
        return None

    @staticmethod
    def _finish_observation(observation: Any | None, **kwargs: Any) -> None:
        if observation is None:
            return
        for method_name in ("end", "update"):
            method = getattr(observation, method_name, None)
            if callable(method):
                try:
                    method(**kwargs)
                    return
                except TypeError:
                    try:
                        method()
                        return
                    except Exception:
                        logger.debug("Langfuse observation finish failed", exc_info=True)
                except Exception:
                    logger.debug("Langfuse observation finish failed", exc_info=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        """Initialize the runtime.

        Loads Agent identity from *app_dir* and marks the runtime ready.

        Raises:
            FileNotFoundError: If SOUL.md is missing from *app_dir*.
        """
        self._identity_loader = IdentityLoader(self.app_dir)
        await self._identity_loader.load()
        hb_config = self.config.get("heartbeat", {})
        if hb_config.get("enabled", True):
            self._heartbeat_checker = HeartbeatChecker(self.agent_id, hb_config)
        self.is_initialized = True
        logger.info("AgentRuntime '%s' initialized", self.agent_id)

    # ------------------------------------------------------------------
    # Public trigger entry point
    # ------------------------------------------------------------------

    async def trigger_event(
        self,
        event_name: str,
        *,
        focus: str | None = None,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Trigger an Agent run from an external event (cron, webhook, etc.).

        This is the primary API consumed by :class:`CronTriggerRegistry` and
        future trigger adapters.  It creates an :class:`AgentRunContext` and
        calls :meth:`run`.

        Args:
            event_name: Human-readable event name used as the run trigger.
            focus: Optional focus tag to narrow Skill selection.
            payload: Arbitrary context forwarded to the decision loop.
            tenant_id: Multi-tenancy identifier.

        Returns:
            Run result dict (see :meth:`run`).
        """
        if not isinstance(event_name, str) or not event_name.strip():
            raise ValueError("event_name must be a non-empty string")
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id must be a non-empty string")
        normalized_event_name = event_name.strip()
        normalized_tenant_id = tenant_id.strip()
        if isinstance(focus, str):
            focus = focus.strip() or None
        elif focus is not None:
            focus = None
        if payload is None:
            normalized_payload: dict[str, Any] = {}
        elif not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")
        else:
            normalized_payload = dict(payload)
        context = AgentRunContext(
            agent_id=self.agent_id,
            trigger=normalized_event_name,
            payload=normalized_payload,
            focus=focus,
            tenant_id=normalized_tenant_id,
        )
        return await self.run(context)

    # ------------------------------------------------------------------
    # Core run method
    # ------------------------------------------------------------------

    async def run(self, context: AgentRunContext) -> dict[str, Any]:
        """Execute a full Agent run for *context*.

        Args:
            context: Run context including trigger source, focus, and payload.

        Returns:
            ``{"status": "completed"|"skipped", "run_id": str, ...}``

        Raises:
            RuntimeError: If :meth:`setup` has not been called yet.
        """
        if not self.is_initialized:
            raise RuntimeError(
                "AgentRuntime.setup() must be called before run()"
            )

        logger.info(
            "Agent run started agent_id=%s run_id=%s trigger=%s focus=%s",
            context.agent_id,
            context.run_id,
            context.trigger,
            context.focus,
        )

        if context.trigger == "heartbeat" and self._heartbeat_checker is not None:
            has_events = self._heartbeat_payload_has_events(context.payload)
            if not has_events:
                has_events = await self._heartbeat_checker.check_events()
            if not has_events:
                logger.info(
                    "Heartbeat no events, skipping LLM agent_id=%s run_id=%s",
                    context.agent_id,
                    context.run_id,
                )
                return {
                    "status": "skipped",
                    "run_id": context.run_id,
                    "reason": "heartbeat_no_events",
                }

        trace = self._create_trace(context)

        run_timeout_raw = self.config.get(
            "run_timeout_seconds", _DEFAULT_RUN_TIMEOUT_SECONDS
        )
        if isinstance(run_timeout_raw, bool):
            run_timeout = _DEFAULT_RUN_TIMEOUT_SECONDS
        else:
            try:
                run_timeout = float(run_timeout_raw)
            except (TypeError, ValueError):
                run_timeout = _DEFAULT_RUN_TIMEOUT_SECONDS
        if run_timeout <= 0:
            run_timeout = _DEFAULT_RUN_TIMEOUT_SECONDS
        if not math.isfinite(run_timeout):
            run_timeout = _DEFAULT_RUN_TIMEOUT_SECONDS
        try:
            decision_loop_fn = self._decision_loop
            decision_loop_params = inspect.signature(decision_loop_fn).parameters
            if len(decision_loop_params) >= 2:
                decision_loop_coro = decision_loop_fn(context, trace)
            else:
                decision_loop_coro = decision_loop_fn(context)
            result = await asyncio.wait_for(
                decision_loop_coro,
                timeout=run_timeout,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Agent run timed out agent_id=%s run_id=%s timeout=%ss",
                context.agent_id,
                context.run_id,
                run_timeout,
            )
            self._update_trace(
                trace,
                status="error",
                output=f"run timed out after {run_timeout:.1f}s",
            )
            return {
                "status": "failed",
                "run_id": context.run_id,
                "error": f"run timed out after {run_timeout:.1f}s",
            }

        logger.info(
            "Agent run completed agent_id=%s run_id=%s iterations=%s",
            context.agent_id,
            context.run_id,
            result.get("iterations", 0),
        )
        self._update_trace(trace, status="success", output=result)
        return {"status": "completed", "run_id": context.run_id, **result}

    # ------------------------------------------------------------------
    # Decision loop
    # ------------------------------------------------------------------

    async def _decision_loop(self, context: AgentRunContext, trace: Any | None = None) -> dict[str, Any]:
        """Core LLM function-calling loop.

        1. Build system prompt (identity + skills knowledge)
        2. Build visible tools list
        3. Iterate: call LLM → execute tool calls → repeat until no tool calls
        """
        # Build context components
        skills_context = self._build_skills_context(context)
        visible_tools = await self._get_visible_tools(context)
        messages = self._build_messages(context, skills_context, visible_tools)

        max_iterations_raw = self.config.get(
            "max_function_calls", _DEFAULT_MAX_ITERATIONS
        )
        if isinstance(max_iterations_raw, bool):
            max_iterations = _DEFAULT_MAX_ITERATIONS
        else:
            try:
                max_iterations = max(1, int(max_iterations_raw))
            except (TypeError, ValueError):
                max_iterations = _DEFAULT_MAX_ITERATIONS
        llm_timeout_raw = self.config.get(
            "llm_timeout_seconds", _DEFAULT_LLM_TIMEOUT_SECONDS
        )
        if isinstance(llm_timeout_raw, bool):
            llm_timeout = _DEFAULT_LLM_TIMEOUT_SECONDS
        else:
            try:
                llm_timeout = float(llm_timeout_raw)
            except (TypeError, ValueError):
                llm_timeout = _DEFAULT_LLM_TIMEOUT_SECONDS
        if llm_timeout <= 0:
            llm_timeout = _DEFAULT_LLM_TIMEOUT_SECONDS
        if not math.isfinite(llm_timeout):
            llm_timeout = _DEFAULT_LLM_TIMEOUT_SECONDS
        model_used = self.model
        iteration = 0
        for _ in range(max_iterations):
            iteration += 1
            if self._router is not None:
                from owlclaw.governance.visibility import RunContext

                task_type = context.payload.get("task_type") or self.config.get("default_task_type") or "default"
                run_ctx = RunContext(tenant_id=context.tenant_id)
                selection = await self._router.select_model(task_type, run_ctx)
                if selection is not None and getattr(selection, "model", None):
                    model_used = selection.model

            call_kwargs: dict[str, Any] = {
                "model": model_used,
                "messages": messages,
            }
            if visible_tools:
                call_kwargs["tools"] = visible_tools
                call_kwargs["tool_choice"] = "auto"

            try:
                response = await asyncio.wait_for(
                    llm_integration.acompletion(**call_kwargs),
                    timeout=llm_timeout,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "LLM call timed out agent_id=%s run_id=%s timeout=%ss",
                    context.agent_id,
                    context.run_id,
                    llm_timeout,
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"LLM call timed out after {llm_timeout:.1f}s.",
                    }
                )
                break
            message = self._extract_assistant_message(response)
            if message is None:
                logger.error(
                    "Invalid LLM response shape agent_id=%s run_id=%s",
                    context.agent_id,
                    context.run_id,
                )
                messages.append({
                    "role": "assistant",
                    "content": "LLM response missing assistant message.",
                })
                break

            # Append assistant turn to conversation
            messages.append(self._assistant_message_to_dict(message))

            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                # LLM decided it is done
                break

            # Execute each tool call and add results
            for idx, tc in enumerate(tool_calls):
                tool_result = await self._execute_tool(tc, context, trace=trace)
                tool_call_id = getattr(tc, "id", None) or f"tool_call_{iteration}_{idx}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result, default=str),
                })

        final_content = ""
        if messages and messages[-1].get("role") == "assistant":
            final_content = messages[-1].get("content") or ""

        return {
            "iterations": iteration,
            "final_response": final_content,
            "tool_calls_total": sum(
                1
                for m in messages
                if m.get("role") == "tool"
            ),
        }

    @staticmethod
    def _assistant_message_to_dict(message: Any) -> dict[str, Any]:
        """Normalize LLM message object to a serializable assistant dict."""
        if isinstance(message, dict):
            normalized = dict(message)
            normalized.setdefault("role", "assistant")
            return normalized
        model_dump = getattr(message, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(exclude_none=True)
            if isinstance(dumped, dict):
                dumped.setdefault("role", "assistant")
                return dumped
        content = getattr(message, "content", "")
        tool_calls = getattr(message, "tool_calls", None)
        out: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            out["tool_calls"] = tool_calls
        return out

    @staticmethod
    def _extract_assistant_message(response: Any) -> Any | None:
        """Extract assistant message from completion response."""
        choices = (
            response.get("choices")
            if isinstance(response, dict)
            else getattr(response, "choices", None)
        )
        if not isinstance(choices, list | tuple) or not choices:
            return None
        first = choices[0]
        if isinstance(first, dict):
            return first.get("message")
        return getattr(first, "message", None)

    @staticmethod
    def _heartbeat_payload_has_events(payload: dict[str, Any]) -> bool:
        """Return True when heartbeat payload already indicates pending events.

        This path keeps Heartbeat checks zero-I/O by trusting trigger-side
        in-memory signals carried in payload.
        """
        if not payload:
            return False
        if payload.get("has_events") is True:
            return True
        pending = payload.get("pending_events")
        if isinstance(pending, list | tuple | set) and len(pending) > 0:
            return True
        count = payload.get("event_count")
        return bool(
            isinstance(count, int | float)
            and not isinstance(count, bool)
            and count > 0
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tool(
        self, tool_call: Any, context: AgentRunContext, *, trace: Any | None = None
    ) -> Any:
        """Dispatch a single LLM tool call to the capability registry.

        Falls back to a descriptive error dict if the capability is not
        registered or raises, so the LLM can handle it gracefully.
        """
        function = getattr(tool_call, "function", None)
        tool_name = getattr(function, "name", None)
        if not isinstance(tool_name, str) or not tool_name.strip():
            return {"error": "Invalid tool call: missing function name"}
        invalid_arguments = False
        invalid_reason = ""
        try:
            raw_args = function.arguments
            arguments: dict[str, Any] = (
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            )
        except json.JSONDecodeError:
            invalid_arguments = True
            invalid_reason = "arguments must be valid JSON object"
            arguments = {}
        except AttributeError:
            invalid_arguments = True
            invalid_reason = "missing tool arguments"
            arguments = {}
        if not isinstance(arguments, dict):
            invalid_arguments = True
            invalid_reason = "arguments must be a JSON object"
            arguments = {}
        if invalid_arguments:
            return {
                "error": f"Invalid arguments for tool '{tool_name}': {invalid_reason}",
            }

        if self.builtin_tools is not None and self.builtin_tools.is_builtin(tool_name):
            from owlclaw.agent.tools import BuiltInToolsContext

            ctx = BuiltInToolsContext(
                agent_id=context.agent_id,
                run_id=context.run_id,
                tenant_id=context.tenant_id,
            )
            try:
                return await self.builtin_tools.execute(tool_name, arguments, ctx)
            except Exception as exc:
                logger.exception("Built-in tool '%s' failed", tool_name)
                return {"error": str(exc)}

        if self.registry is None:
            return {"error": f"No capability registry configured for tool '{tool_name}'"}

        invoke_arguments = self._normalize_capability_arguments(arguments, context)
        observation = self._observe_tool(
            trace,
            "tool_execution",
            {"tool": tool_name, "run_id": context.run_id, "arguments": invoke_arguments},
        )
        start_ns = time.perf_counter_ns()
        try:
            result = await self.registry.invoke_handler(tool_name, **invoke_arguments)
            execution_time_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            if self._ledger is not None:
                meta = self.registry.get_capability_metadata(tool_name)
                task_type = (meta.get("task_type") or "unknown") if meta else "unknown"
                decision_reasoning = self._build_tool_decision_reasoning(meta, context)
                await self._ledger.record_execution(
                    tenant_id=context.tenant_id,
                    agent_id=context.agent_id,
                    run_id=context.run_id,
                    capability_name=tool_name,
                    task_type=task_type,
                    input_params=invoke_arguments,
                    output_result=result if isinstance(result, dict) else {"result": result},
                    decision_reasoning=decision_reasoning,
                    execution_time_ms=execution_time_ms,
                    llm_model="",
                    llm_tokens_input=0,
                    llm_tokens_output=0,
                    estimated_cost=Decimal("0"),
                        status="success",
                        error_message=None,
                    )
            self._finish_observation(
                observation,
                output=result if isinstance(result, dict) else {"result": result},
                status="success",
            )
            return result
        except ValueError:
            self._finish_observation(observation, status="error", output={"error": "not registered"})
            return {"error": f"Capability '{tool_name}' is not registered"}
        except Exception as exc:
            logger.exception("Tool '%s' failed", tool_name)
            if self._ledger is not None:
                execution_time_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                meta = self.registry.get_capability_metadata(tool_name)
                task_type = (meta.get("task_type") or "unknown") if meta else "unknown"
                decision_reasoning = self._build_tool_decision_reasoning(meta, context)
                try:
                    await self._ledger.record_execution(
                        tenant_id=context.tenant_id,
                        agent_id=context.agent_id,
                        run_id=context.run_id,
                        capability_name=tool_name,
                        task_type=task_type,
                        input_params=invoke_arguments,
                        output_result=None,
                        decision_reasoning=decision_reasoning,
                        execution_time_ms=execution_time_ms,
                        llm_model="",
                        llm_tokens_input=0,
                        llm_tokens_output=0,
                        estimated_cost=Decimal("0"),
                        status="error",
                        error_message=str(exc),
                    )
                except Exception as ledger_exc:
                    logger.exception("Ledger record_execution failed: %s", ledger_exc)
            self._finish_observation(observation, status="error", output={"error": str(exc)})
            return {"error": str(exc)}

    def _normalize_capability_arguments(
        self, arguments: dict[str, Any], context: AgentRunContext
    ) -> dict[str, Any]:
        """Normalize tool-call arguments before capability invocation.

        Supports both direct argument objects and legacy wrapped payloads:
        ``{"kwargs": {...}}``.

        When no arguments are provided, inject a default ``session`` object so
        handlers using the common ``handler(session)`` signature still work.
        """
        if "kwargs" in arguments and len(arguments) == 1 and isinstance(arguments["kwargs"], dict):
            normalized = dict(arguments["kwargs"])
        else:
            normalized = dict(arguments)

        if normalized:
            return normalized

        return {
            "session": {
                "agent_id": context.agent_id,
                "run_id": context.run_id,
                "trigger": context.trigger,
                "focus": context.focus,
                "payload": context.payload,
                "tenant_id": context.tenant_id,
            }
        }

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self,
        skills_context: str,
        visible_tools: list[dict[str, Any]],
    ) -> str:
        """Assemble the system prompt from identity, skills, and tool count."""
        assert self._identity_loader is not None
        identity = self._identity_loader.get_identity()

        parts: list[str] = []

        # Identity
        parts.append("# Your Identity\n")
        parts.append(identity["soul"])

        # Capabilities summary from IDENTITY.md
        if identity["capabilities_summary"]:
            parts.append("\n# Your Capabilities\n")
            parts.append(identity["capabilities_summary"])

        # Skills knowledge
        if skills_context:
            parts.append("\n# Business Knowledge\n")
            parts.append(skills_context)

        # Tool count hint
        if visible_tools:
            parts.append(
                f"\n# Available Tools\n"
                f"You have access to {len(visible_tools)} tools. "
                "Use function calling to choose actions.\n"
            )

        return "".join(parts)

    def _build_user_message(self, context: AgentRunContext) -> str:
        """Build the first user message from trigger context."""
        parts: list[str] = [f"Trigger: {context.trigger}"]

        if context.focus:
            parts.append(f"Focus: {context.focus}")

        if context.payload:
            parts.append(f"Context: {json.dumps(context.payload, default=str)}")

        raw_message = "\n".join(parts)
        sanitized = self._input_sanitizer.sanitize(raw_message, source=context.trigger)
        if sanitized.changed:
            self._security_audit.record(
                event_type="sanitization",
                source=context.trigger,
                details={
                    "agent_id": context.agent_id,
                    "run_id": context.run_id,
                    "modifications": sanitized.modifications,
                },
            )
        return sanitized.sanitized

    def _build_messages(
        self,
        context: AgentRunContext,
        skills_context: str,
        visible_tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build initial messages with strict system/user role separation."""
        system_prompt = self._build_system_prompt(skills_context, visible_tools)
        user_message = self._build_user_message(context)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    def _build_skills_context(self, context: AgentRunContext) -> str:
        """Return Skills knowledge string, optionally filtered by focus."""
        if self.knowledge_injector is None or self.registry is None:
            return ""

        all_skill_names = list(self.registry.handlers.keys())
        if not all_skill_names:
            return ""

        # Focus filter: if focus is set, prefer skills whose tag list includes it
        if context.focus:
            focused = [
                n for n in all_skill_names
                if self._skill_has_focus(n, context.focus)
            ]
            if not focused:
                return ""
            skill_names = focused
        else:
            skill_names = all_skill_names

        return self.knowledge_injector.get_skills_knowledge(skill_names)

    def _skill_has_focus(self, skill_name: str, focus: str) -> bool:
        """Return True if the skill declares *focus* in owlclaw.focus.

        Falls back to metadata.tags for backwards compatibility.
        """
        if self.registry is None:
            return False
        try:
            skill = self.registry.skills_loader.get_skill(skill_name)
        except Exception as exc:
            logger.warning("Failed to resolve skill focus metadata for %s: %s", skill_name, exc)
            return False
        if skill is None:
            return False
        target = focus.strip().lower()
        if not target:
            return False

        declared_focus = skill.owlclaw_config.get("focus", [])
        if isinstance(declared_focus, str):
            declared_focus = [declared_focus]
        if isinstance(declared_focus, list):
            normalized_focus = {str(item).strip().lower() for item in declared_focus if str(item).strip()}
            if normalized_focus:
                return target in normalized_focus

        tags = skill.metadata.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if isinstance(tags, list):
            normalized_tags = {str(item).strip().lower() for item in tags if str(item).strip()}
            return target in normalized_tags
        return False

    # ------------------------------------------------------------------
    # Visible tools
    # ------------------------------------------------------------------

    async def _get_visible_tools(
        self, context: AgentRunContext
    ) -> list[dict[str, Any]]:
        """Build the governance-filtered OpenAI-style function schema list."""
        all_schemas: list[dict[str, Any]] = []

        if self.builtin_tools is not None:
            all_schemas.extend(self.builtin_tools.get_tool_schemas())

        if self.registry is not None:
            all_schemas.extend(self._capability_schemas())

        if self.visibility_filter is None:
            return all_schemas

        builtin_names = {s["function"]["name"] for s in all_schemas if self.builtin_tools and self.builtin_tools.is_builtin(s["function"]["name"])}
        cap_schemas = [s for s in all_schemas if s["function"]["name"] not in builtin_names]
        if not cap_schemas:
            return all_schemas

        # Use governance VisibilityFilter for capabilities only (with task_type/constraints from registry)
        from owlclaw.governance.visibility import CapabilityView, RunContext

        cap_list = self.registry.list_capabilities()
        name_to_meta = {c["name"]: c for c in cap_list}
        cap_views = [
            CapabilityView(
                name=s["function"]["name"],
                description=s["function"].get("description", ""),
                task_type=name_to_meta.get(s["function"]["name"], {}).get("task_type"),
                constraints=name_to_meta.get(s["function"]["name"], {}).get("constraints") or {},
                focus=name_to_meta.get(s["function"]["name"], {}).get("focus"),
                risk_level=name_to_meta.get(s["function"]["name"], {}).get("risk_level"),
                requires_confirmation=name_to_meta.get(s["function"]["name"], {}).get("requires_confirmation"),
            )
            for s in cap_schemas
        ]
        confirmed = self._extract_confirmed_capabilities(context.payload)
        run_ctx = RunContext(
            tenant_id=context.tenant_id,
            confirmed_capabilities=confirmed or None,
        )
        visible_caps = await self.visibility_filter.filter_capabilities(
            cap_views, context.agent_id, run_ctx
        )
        visible_names = {cap.name for cap in visible_caps}
        filtered_caps = [s for s in cap_schemas if s["function"]["name"] in visible_names]
        return all_schemas[: len(all_schemas) - len(cap_schemas)] + filtered_caps

    @staticmethod
    def _extract_confirmed_capabilities(payload: dict[str, Any]) -> set[str]:
        """Parse confirmed capabilities from payload in list/set/tuple/csv forms."""
        confirmed_raw = payload.get("confirmed_capabilities")
        if isinstance(confirmed_raw, list | tuple | set):
            out: set[str] = set()
            for name in confirmed_raw:
                if name is None:
                    continue
                normalized = str(name).strip()
                if normalized:
                    out.add(normalized)
            return out
        if isinstance(confirmed_raw, str):
            return {
                part.strip()
                for part in confirmed_raw.split(",")
                if part.strip()
            }
        return set()

    def _build_tool_decision_reasoning(
        self,
        capability_meta: dict[str, Any] | None,
        context: AgentRunContext,
    ) -> str:
        """Build compact audit payload for capability execution records."""
        meta = capability_meta or {}
        confirmed = self._extract_confirmed_capabilities(context.payload)
        payload = {
            "source": "runtime_tool_execution",
            "trigger": context.trigger,
            "focus": context.focus,
            "risk_level": _normalize_risk_level(meta.get("risk_level", "low")),
            "requires_confirmation": _coerce_confirmation_flag(meta.get("requires_confirmation", False)),
            "confirmed": meta.get("name") in confirmed if meta.get("name") else False,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _capability_schemas(self) -> list[dict[str, Any]]:
        """Convert registered capabilities to OpenAI function schemas."""
        if self.registry is None:
            return []

        schemas: list[dict[str, Any]] = []
        capabilities = sorted(
            self.registry.list_capabilities(),
            key=lambda c: str(c.get("name", "")),
        )
        for capability in capabilities:
            schemas.append({
                "type": "function",
                "function": {
                    "name": capability["name"],
                    "description": capability.get("description") or "",
                    "parameters": {
                        "type": "object",
                        "description": "Arguments for this capability.",
                        "additionalProperties": True,
                        "required": [],
                    },
                },
            })
        return schemas
