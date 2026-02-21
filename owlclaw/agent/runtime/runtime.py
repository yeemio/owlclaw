"""AgentRuntime — core orchestrator for Agent execution.

Responsibilities:
- Load Agent identity (SOUL.md, IDENTITY.md) via IdentityLoader
- Inject Skills knowledge into the system prompt
- Build the governance-filtered visible tools list
- Execute the LLM function-calling decision loop (via litellm)
- Provide trigger_event() as the public entry point for cron/webhook/etc.

This MVP implementation omits:
- Long-term memory (vector search) — returns empty; add later with MemorySystem
- HeartbeatChecker — heartbeat trigger bypasses LLM and returns immediately
- Langfuse tracing — optional; add later with integrations-langfuse
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any

import litellm

from owlclaw.agent.runtime.context import AgentRunContext
from owlclaw.agent.runtime.identity import IdentityLoader

if TYPE_CHECKING:
    from owlclaw.capabilities.knowledge import KnowledgeInjector
    from owlclaw.capabilities.registry import CapabilityRegistry
    from owlclaw.governance.visibility import VisibilityFilter

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_ITERATIONS = 50


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
        model: LLM model string accepted by litellm (e.g.
            ``"gpt-4o"``, ``"anthropic/claude-3-5-sonnet-20241022"``).
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
        model: str = _DEFAULT_MODEL,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.app_dir = app_dir
        self.registry = registry
        self.knowledge_injector = knowledge_injector
        self.visibility_filter = visibility_filter
        self.model = model
        self.config: dict[str, Any] = config or {}

        self._identity_loader: IdentityLoader | None = None
        self.is_initialized = False

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
        context = AgentRunContext(
            agent_id=self.agent_id,
            trigger=event_name,
            payload=payload or {},
            focus=focus,
            tenant_id=tenant_id,
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

        result = await self._decision_loop(context)

        logger.info(
            "Agent run completed agent_id=%s run_id=%s iterations=%s",
            context.agent_id,
            context.run_id,
            result.get("iterations", 0),
        )
        return {"status": "completed", "run_id": context.run_id, **result}

    # ------------------------------------------------------------------
    # Decision loop
    # ------------------------------------------------------------------

    async def _decision_loop(self, context: AgentRunContext) -> dict[str, Any]:
        """Core LLM function-calling loop.

        1. Build system prompt (identity + skills knowledge)
        2. Build visible tools list
        3. Iterate: call LLM → execute tool calls → repeat until no tool calls
        """
        # Build context components
        skills_context = self._build_skills_context(context)
        visible_tools = await self._get_visible_tools(context)
        system_prompt = self._build_system_prompt(skills_context, visible_tools)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add user-facing trigger message
        user_msg = self._build_user_message(context)
        messages.append({"role": "user", "content": user_msg})

        max_iterations: int = self.config.get(
            "max_function_calls", _DEFAULT_MAX_ITERATIONS
        )
        iteration = 0

        for iteration in range(max_iterations):
            call_kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if visible_tools:
                call_kwargs["tools"] = visible_tools
                call_kwargs["tool_choice"] = "auto"

            response = await litellm.acompletion(**call_kwargs)
            message = response.choices[0].message

            # Append assistant turn to conversation
            messages.append(message.model_dump(exclude_none=True))

            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                # LLM decided it is done
                break

            # Execute each tool call and add results
            for tc in tool_calls:
                tool_result = await self._execute_tool(tc, context)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, default=str),
                })

        final_content = ""
        if messages and messages[-1].get("role") == "assistant":
            final_content = messages[-1].get("content") or ""

        return {
            "iterations": iteration + 1,
            "final_response": final_content,
            "tool_calls_total": sum(
                1
                for m in messages
                if m.get("role") == "tool"
            ),
        }

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tool(
        self, tool_call: Any, context: AgentRunContext
    ) -> Any:
        """Dispatch a single LLM tool call to the capability registry.

        Falls back to a descriptive error dict if the capability is not
        registered or raises, so the LLM can handle it gracefully.
        """
        tool_name: str = tool_call.function.name
        try:
            raw_args = tool_call.function.arguments
            arguments: dict[str, Any] = (
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            )
        except (json.JSONDecodeError, AttributeError):
            arguments = {}

        if self.registry is None:
            return {"error": f"No capability registry configured for tool '{tool_name}'"}

        try:
            result = await self.registry.invoke_handler(tool_name, **arguments)
            return result
        except ValueError:
            return {"error": f"Capability '{tool_name}' is not registered"}
        except Exception as exc:
            logger.exception("Tool '%s' failed", tool_name)
            return {"error": str(exc)}

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
        parts: list[str] = []

        if context.focus:
            parts.append(f"Focus: {context.focus}")

        if context.payload:
            parts.append(f"Context: {json.dumps(context.payload, default=str)}")

        if not parts:
            parts.append(
                f"Event '{context.trigger}' fired. Assess the situation "
                "and take appropriate action."
            )

        return "\n".join(parts)

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
            skill_names = focused if focused else all_skill_names
        else:
            skill_names = all_skill_names

        return self.knowledge_injector.get_skills_knowledge(skill_names)

    def _skill_has_focus(self, skill_name: str, focus: str) -> bool:
        """Return True if the skill's tags include *focus*."""
        if self.registry is None:
            return False
        skill = self.registry.skills_loader.get_skill(skill_name)
        if skill is None:
            return False
        tags = skill.metadata.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        return focus in tags

    # ------------------------------------------------------------------
    # Visible tools
    # ------------------------------------------------------------------

    async def _get_visible_tools(
        self, context: AgentRunContext
    ) -> list[dict[str, Any]]:
        """Build the governance-filtered OpenAI-style function schema list."""
        if self.registry is None:
            return []

        all_schemas = self._capability_schemas()

        if self.visibility_filter is None:
            return all_schemas

        # Use governance VisibilityFilter
        from owlclaw.governance.visibility import CapabilityView, RunContext

        cap_views = [
            CapabilityView(
                name=s["function"]["name"],
                description=s["function"].get("description", ""),
                task_type=None,
                constraints={},
            )
            for s in all_schemas
        ]
        run_ctx = RunContext(tenant_id=context.tenant_id)
        visible_caps = await self.visibility_filter.filter_capabilities(
            cap_views, context.agent_id, run_ctx
        )
        visible_names = {cap.name for cap in visible_caps}
        return [s for s in all_schemas if s["function"]["name"] in visible_names]

    def _capability_schemas(self) -> list[dict[str, Any]]:
        """Convert registered capabilities to OpenAI function schemas."""
        if self.registry is None:
            return []

        schemas: list[dict[str, Any]] = []
        for capability in self.registry.list_capabilities():
            schemas.append({
                "type": "function",
                "function": {
                    "name": capability["name"],
                    "description": capability.get("description") or "",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "kwargs": {
                                "type": "object",
                                "description": "Keyword arguments for this capability",
                            }
                        },
                        "required": [],
                    },
                },
            })
        return schemas
