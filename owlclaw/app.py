"""OwlClaw main application class."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from owlclaw.agent import AgentRuntime
from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.governance.visibility import CapabilityView
from owlclaw.triggers.cron import CronTriggerRegistry

logger = logging.getLogger(__name__)


def _dict_to_capability_view(d: dict[str, Any]) -> CapabilityView:
    """Build CapabilityView from registry list_capabilities() item."""
    return CapabilityView(
        name=d.get("name", ""),
        description=d.get("description", ""),
        task_type=d.get("task_type"),
        constraints=d.get("constraints") or {},
        focus=d.get("focus") or [],
        risk_level=d.get("risk_level") or "low",
        requires_confirmation=d.get("requires_confirmation"),
    )


class OwlClaw:
    """OwlClaw application — the entry point for business applications.

    Usage::

        from owlclaw import OwlClaw

        app = OwlClaw("mionyee-trading")
        app.mount_skills("./capabilities/")

        @app.handler("entry-monitor")
        async def check_entry(session) -> dict:
            ...

        app.run()
    """

    def __init__(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        self.name = name.strip()
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._states: dict[str, Callable[..., Any]] = {}
        self._skills_path: str | None = None
        self._config: dict[str, Any] = {}

        # Capabilities components (initialized by mount_skills)
        self.skills_loader: SkillsLoader | None = None
        self.registry: CapabilityRegistry | None = None
        self.knowledge_injector: KnowledgeInjector | None = None

        # Governance (optional; initialized when configure(governance=...) is used)
        self._governance_config: dict[str, Any] | None = None
        self._visibility_filter: Any = None
        self._router: Any = None
        self._ledger: Any = None

        # Cron triggers (Task 4.3)
        self.cron_registry: CronTriggerRegistry = CronTriggerRegistry(self)

    def mount_skills(self, path: str) -> None:
        """Mount Skills from a business application directory.

        Scans the directory for SKILL.md files following the Agent Skills spec,
        loads their frontmatter metadata, and registers them as capabilities.

        Args:
            path: Path to capabilities directory containing SKILL.md files
        """
        self._skills_path = path

        # Initialize Skills Loader
        self.skills_loader = SkillsLoader(Path(path))
        skills = self.skills_loader.scan()

        # Initialize Registry and Knowledge Injector
        self.registry = CapabilityRegistry(self.skills_loader)
        self.knowledge_injector = KnowledgeInjector(self.skills_loader)

        logger.info("Loaded %d Skills from %s", len(skills), path)

    def handler(self, skill_name: str) -> Callable:
        """Decorator to register a capability handler associated with a Skill.

        The handler function is called when the Agent decides to invoke this capability
        via function calling. The skill_name must match a loaded SKILL.md's `name` field.

        Args:
            skill_name: Name of the Skill this handler implements

        Raises:
            RuntimeError: If mount_skills() hasn't been called yet
        """

        def decorator(fn: Callable) -> Callable:
            if not self.registry:
                raise RuntimeError(
                    "Must call mount_skills() before registering handlers"
                )

            self.registry.register_handler(skill_name, fn)
            self._handlers[skill_name] = fn
            return fn

        return decorator

    def cron(
        self,
        expression: str,
        *,
        event_name: str | None = None,
        focus: str | None = None,
        description: str | None = None,
        fallback: Callable | None = None,
        **kwargs: Any,
    ) -> Callable:
        """Decorator to register a function as a cron-triggered task.

        The decorated function becomes the default fallback handler unless
        *fallback* is explicitly provided.  If *event_name* is omitted, the
        function's ``__name__`` is used.

        Args:
            expression: 5-field cron expression (e.g. ``"0 9 * * 1-5"``).
            event_name: Unique identifier for this trigger.  Defaults to the
                decorated function's ``__name__``.
            focus: Optional focus tag that narrows which Skills the Agent loads
                when this cron fires.
            description: Human-readable description stored in the config.
            fallback: Explicit fallback callable.  If omitted, the decorated
                function itself is used as the fallback.
            **kwargs: Additional CronTriggerConfig fields such as
                ``max_daily_runs``, ``cooldown_seconds``, ``migration_weight``,
                ``priority``, etc.

        Returns:
            The original function (decorator is transparent).

        Raises:
            ValueError: If the cron expression is invalid or *event_name* is
                already registered.

        Example::

            @app.cron("0 9 * * 1-5", focus="market_open", max_daily_runs=1)
            async def morning_decision():
                \"\"\"Run every weekday at 09:00.\"\"\"
                ...
        """
        from functools import wraps

        def decorator(fn: Callable) -> Callable:
            name = event_name if event_name is not None else fn.__name__
            handler = fallback if fallback is not None else fn

            self.cron_registry.register(
                event_name=name,
                expression=expression,
                focus=focus,
                fallback_handler=handler,
                description=description or (fn.__doc__ or "").strip() or None,
                **kwargs,
            )

            @wraps(fn)
            async def wrapper(*args: Any, **kw: Any) -> Any:
                if inspect.iscoroutinefunction(fn):
                    return await fn(*args, **kw)
                return fn(*args, **kw)

            return wrapper

        return decorator

    def state(self, name: str) -> Callable:
        """Decorator to register a state provider.

        State providers are called by the Agent's query_state built-in tool
        to get current business state snapshots.

        Args:
            name: Name of the state this provider supplies

        Raises:
            RuntimeError: If mount_skills() hasn't been called yet
        """

        def decorator(fn: Callable) -> Callable:
            if not self.registry:
                raise RuntimeError(
                    "Must call mount_skills() before registering states"
                )

            self.registry.register_state(name, fn)
            self._states[name] = fn
            return fn

        return decorator

    def configure(self, **kwargs: Any) -> None:
        """Configure Agent identity, heartbeat, governance, etc.

        Accepts: soul, identity, heartbeat_interval_minutes, governance (dict), and other Agent config.
        """
        self._config.update(kwargs)
        if "governance" in kwargs:
            self._governance_config = kwargs["governance"]

    def _ensure_governance(self) -> None:
        """Create VisibilityFilter, Router, Ledger from _governance_config if not yet created."""
        if self._governance_config is None or self._visibility_filter is not None:
            return
        from owlclaw.governance import (
            BudgetConstraint,
            CircuitBreakerConstraint,
            Ledger,
            RateLimitConstraint,
            RiskConfirmationConstraint,
            Router,
            TimeConstraint,
            VisibilityFilter,
        )

        cfg = self._governance_config
        self._visibility_filter = VisibilityFilter()

        # Time constraint (no Ledger dependency)
        time_cfg = (cfg.get("visibility") or {}).get("time") or {}
        self._visibility_filter.register_evaluator(TimeConstraint(time_cfg))
        risk_cfg = (cfg.get("visibility") or {}).get("risk_confirmation") or {}
        self._visibility_filter.register_evaluator(
            RiskConfirmationConstraint(risk_cfg)
        )

        session_factory = cfg.get("session_factory")
        ledger = None
        if session_factory is not None:
            ledger = Ledger(
                session_factory,
                batch_size=cfg.get("ledger", {}).get("batch_size", 10)
                if isinstance(cfg.get("ledger"), dict)
                else 10,
                flush_interval=cfg.get("ledger", {}).get("flush_interval", 5.0)
                if isinstance(cfg.get("ledger"), dict)
                else 5.0,
            )
            self._ledger = ledger
            budget_cfg = (cfg.get("visibility") or {}).get("budget") or {}
            self._visibility_filter.register_evaluator(
                BudgetConstraint(ledger, budget_cfg)
            )
            self._visibility_filter.register_evaluator(RateLimitConstraint(ledger))
            cb_cfg = (cfg.get("visibility") or {}).get("circuit_breaker") or {}
            self._visibility_filter.register_evaluator(
                CircuitBreakerConstraint(ledger, cb_cfg)
            )

        router_cfg = cfg.get("router") or {}
        self._router = Router(router_cfg)

    async def get_visible_capabilities(
        self,
        agent_id: str,
        tenant_id: str = "default",
        confirmed_capabilities: list[str] | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return capabilities visible after governance filtering (for use in Agent Run).

        Converts registry list to CapabilityView, runs VisibilityFilter, returns
        list of dicts (name, description, task_type, constraints) for visible capabilities.
        """
        if not self.registry:
            return []
        self._ensure_governance()
        raw = self.registry.list_capabilities()
        views = [_dict_to_capability_view(d) for d in raw]
        if self._visibility_filter is None:
            filtered = views
        else:
            from owlclaw.governance.visibility import RunContext

            confirmed: set[str] = set()
            if isinstance(confirmed_capabilities, list):
                confirmed = {
                    c.strip()
                    for c in confirmed_capabilities
                    if isinstance(c, str) and c.strip()
                }
            elif isinstance(confirmed_capabilities, str):
                confirmed = {
                    c.strip()
                    for c in confirmed_capabilities.split(",")
                    if c.strip()
                }
            ctx = RunContext(
                tenant_id=tenant_id,
                confirmed_capabilities=confirmed or None,
            )
            filtered = await self._visibility_filter.filter_capabilities(
                views, agent_id, ctx
            )
            logger.info(
                "VisibilityFilter: %d of %d capabilities visible for agent %s",
                len(filtered),
                len(raw),
                agent_id,
            )
        return [
            {
                "name": c.name,
                "description": c.description,
                "task_type": c.task_type,
                "constraints": c.constraints,
                "focus": c.focus,
                "risk_level": c.risk_level,
                "requires_confirmation": c.requires_confirmation,
            }
            for c in filtered
        ]

    async def get_model_selection(
        self,
        task_type: str,
        tenant_id: str = "default",
    ) -> Any:
        """Return model and fallback chain for the given task_type (for use before LLM call)."""
        self._ensure_governance()
        if self._router is None:
            return None
        from owlclaw.governance.visibility import RunContext

        ctx = RunContext(tenant_id=tenant_id)
        return await self._router.select_model(task_type, ctx)

    async def record_execution(
        self,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        capability_name: str,
        task_type: str,
        input_params: dict[str, Any],
        output_result: dict[str, Any] | None,
        decision_reasoning: str | None,
        execution_time_ms: int,
        llm_model: str,
        llm_tokens_input: int,
        llm_tokens_output: int,
        estimated_cost: Any,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Record one capability execution (for use after capability runs)."""
        self._ensure_governance()
        if self._ledger is None:
            return
        await self._ledger.record_execution(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            capability_name=capability_name,
            task_type=task_type,
            input_params=input_params,
            output_result=output_result,
            decision_reasoning=decision_reasoning,
            execution_time_ms=execution_time_ms,
            llm_model=llm_model,
            llm_tokens_input=llm_tokens_input,
            llm_tokens_output=llm_tokens_output,
            estimated_cost=estimated_cost,
            status=status,
            error_message=error_message,
        )

    async def start_governance(self) -> None:
        """Start governance background tasks (e.g. Ledger writer). Call before run()."""
        self._ensure_governance()
        if self._ledger is not None:
            await self._ledger.start()

    async def stop_governance(self) -> None:
        """Stop governance background tasks. Call on shutdown."""
        if self._ledger is not None:
            await self._ledger.stop()

    def create_agent_runtime(
        self,
        app_dir: str | None = None,
        hatchet_client: Any = None,
    ) -> AgentRuntime:
        """Create an AgentRuntime configured with this app's registry, governance, and built-in tools.

        Must be called after mount_skills(). If *app_dir* is omitted, uses the parent
        directory of the mounted skills path (where SOUL.md and IDENTITY.md are expected).
        If *hatchet_client* is provided, built-in schedule_once and cancel_schedule work.

        Returns:
            AgentRuntime configured with registry, knowledge_injector, visibility_filter,
            ledger, and BuiltInTools (query_state, log_decision).
        """
        if not self.registry or not self.knowledge_injector:
            raise RuntimeError(
                "Must call mount_skills() before create_agent_runtime()"
            )
        from owlclaw.agent import AgentRuntime, BuiltInTools

        resolved_app_dir: str
        if app_dir is not None:
            resolved_app_dir = app_dir
        elif self._skills_path:
            resolved_app_dir = str(Path(self._skills_path).resolve().parent)
        else:
            raise RuntimeError(
                "Cannot determine app_dir: provide app_dir explicitly or call mount_skills() first"
            )

        self._ensure_governance()
        builtin_tools = BuiltInTools(
            capability_registry=self.registry,
            ledger=self._ledger,
            hatchet_client=hatchet_client,
        )
        return AgentRuntime(
            agent_id=self.name,
            app_dir=resolved_app_dir,
            registry=self.registry,
            knowledge_injector=self.knowledge_injector,
            visibility_filter=self._visibility_filter,
            builtin_tools=builtin_tools,
            router=self._router,
            ledger=self._ledger,
        )

    def run(self) -> None:
        """Start the OwlClaw application.

        Initializes the Agent runtime, loads Skills, starts Hatchet worker,
        and begins processing triggers and heartbeats.
        """
        raise RuntimeError(
            "OwlClaw.run() is not implemented yet. "
            "Use create_agent_runtime() and explicit trigger/worker startup."
        )
