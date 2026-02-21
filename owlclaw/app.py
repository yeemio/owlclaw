"""OwlClaw main application class."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.triggers.cron import CronTriggerRegistry

logger = logging.getLogger(__name__)


def _dict_to_capability_view(d: dict[str, Any]) -> "CapabilityView":
    """Build CapabilityView from registry list_capabilities() item."""
    from owlclaw.governance.visibility import CapabilityView

    return CapabilityView(
        name=d.get("name", ""),
        description=d.get("description", ""),
        task_type=d.get("task_type"),
        constraints=d.get("constraints") or {},
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
        self.name = name
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
                return await fn(*args, **kw)

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
            Router,
            TimeConstraint,
            VisibilityFilter,
        )

        cfg = self._governance_config
        self._visibility_filter = VisibilityFilter()

        # Time constraint (no Ledger dependency)
        time_cfg = (cfg.get("visibility") or {}).get("time") or {}
        self._visibility_filter.register_evaluator(TimeConstraint(time_cfg))

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
    ) -> list[dict[str, Any]]:
        """Return capabilities visible after governance filtering (for use in Agent Run).

        Converts registry list to CapabilityView, runs VisibilityFilter, returns
        list of dicts (name, description, task_type, constraints) for visible capabilities.
        """
        if not self.registry:
            return []
        self._ensure_governance()
        if self._visibility_filter is None:
            raw = self.registry.list_capabilities()
            return raw
        from owlclaw.governance.visibility import RunContext

        raw = self.registry.list_capabilities()
        views = [_dict_to_capability_view(d) for d in raw]
        ctx = RunContext(tenant_id=tenant_id)
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

    def run(self) -> None:
        """Start the OwlClaw application.

        Initializes the Agent runtime, loads Skills, starts Hatchet worker,
        and begins processing triggers and heartbeats.
        """
        ...
