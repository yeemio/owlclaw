"""OwlClaw main application class."""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from owlclaw.agent import AgentRuntime
from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.config import ConfigManager
from owlclaw.governance.visibility import CapabilityView
from owlclaw.security.sanitizer import InputSanitizer
from owlclaw.triggers.api import (
    APIKeyAuthProvider,
    APITriggerConfig,
    APITriggerRegistration,
    APITriggerServer,
    BearerTokenAuthProvider,
    GovernanceDecision,
)
from owlclaw.triggers.cron import CronTriggerRegistry
from owlclaw.triggers.db_change import (
    DBChangeTriggerConfig,
    DBChangeTriggerManager,
    DBChangeTriggerRegistration,
    PostgresNotifyAdapter,
)

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


class _AllowAllGovernance:
    async def allow_trigger(self, event_name: str, tenant_id: str) -> bool:  # noqa: ARG002
        return True


class _APIGovernanceBridge:
    def __init__(self, app: OwlClaw) -> None:
        self._app = app

    async def evaluate_request(
        self,
        event_name: str,
        tenant_id: str,
        payload: dict[str, Any],  # noqa: ARG002
    ) -> GovernanceDecision:
        if self._app._governance_config is None:
            return GovernanceDecision(allowed=True)

        limits = self._app._governance_config.get("api_limits", {})
        if not isinstance(limits, dict):
            return GovernanceDecision(allowed=True)

        blocked_events = limits.get("blocked_events", [])
        if isinstance(blocked_events, list) and event_name in blocked_events:
            return GovernanceDecision(allowed=False, status_code=429, reason="rate_limited")

        blocked_tenants = limits.get("blocked_tenants", [])
        if isinstance(blocked_tenants, list) and tenant_id in blocked_tenants:
            return GovernanceDecision(allowed=False, status_code=503, reason="budget_exhausted")

        return GovernanceDecision(allowed=True)


class _RuntimeProxy:
    def __init__(self, app: OwlClaw) -> None:
        self._app = app

    async def trigger_event(
        self,
        event_name: str,
        payload: dict[str, Any],
        focus: str | None = None,
        tenant_id: str = "default",
    ) -> Any:
        if self._app._runtime is None:
            raise RuntimeError("Agent runtime is not started; call app.start() before consuming trigger events.")
        return await self._app._runtime.trigger_event(
            event_name=event_name,
            payload=payload,
            focus=focus,
            tenant_id=tenant_id,
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
        self.db_change_manager: DBChangeTriggerManager | None = None
        self.api_trigger_server: APITriggerServer | None = None
        self._runtime: AgentRuntime | None = None
        self._langchain_adapter: Any = None

    def mount_skills(self, path: str) -> None:
        """Mount Skills from a business application directory.

        Scans the directory for SKILL.md files following the Agent Skills spec,
        loads their frontmatter metadata, and registers them as capabilities.

        Args:
            path: Path to capabilities directory containing SKILL.md files
        """
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")
        normalized_path = path.strip()
        self._skills_path = normalized_path

        # Initialize Skills Loader
        self.skills_loader = SkillsLoader(Path(normalized_path))
        skills = self.skills_loader.scan()

        # Initialize Registry and Knowledge Injector
        self.registry = CapabilityRegistry(self.skills_loader)
        self.knowledge_injector = KnowledgeInjector(self.skills_loader)

        logger.info("Loaded %d Skills from %s", len(skills), normalized_path)

    def handler(
        self,
        skill_name: str,
        *,
        runnable: Any | None = None,
        description: str | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        input_transformer: Callable[[dict[str, Any]], Any] | None = None,
        output_transformer: Callable[[Any], Any] | None = None,
        fallback: str | None = None,
        retry_policy: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        enable_tracing: bool = True,
    ) -> Callable:
        """Decorator to register a capability handler associated with a Skill.

        The handler function is called when the Agent decides to invoke this capability
        via function calling. The skill_name must match a loaded SKILL.md's `name` field.

        Args:
            skill_name: Name of the Skill this handler implements

        Raises:
            RuntimeError: If mount_skills() hasn't been called yet
        """

        if runnable is not None:
            if input_schema is None:
                raise ValueError("input_schema is required when runnable is provided")
            self.register_langchain_runnable(
                name=skill_name,
                runnable=runnable,
                description=description or f"LangChain runnable for {skill_name}",
                input_schema=input_schema,
                output_schema=output_schema,
                input_transformer=input_transformer,
                output_transformer=output_transformer,
                fallback=fallback,
                retry_policy=retry_policy,
                timeout_seconds=timeout_seconds,
                enable_tracing=enable_tracing,
            )

            def passthrough(fn: Callable) -> Callable:
                return fn

            return passthrough

        def decorator(fn: Callable) -> Callable:
            if not self.registry:
                raise RuntimeError(
                    "Must call mount_skills() before registering handlers"
                )

            self.registry.register_handler(skill_name, fn)
            self._handlers[skill_name] = fn
            return fn

        return decorator

    def _get_langchain_adapter(self) -> Any:
        """Build and cache LangChainAdapter using current app config."""
        if self._langchain_adapter is not None:
            return self._langchain_adapter

        from owlclaw.integrations.langchain import LangChainAdapter, LangChainConfig

        integrations_cfg = self._config.get("integrations", {})
        langchain_cfg: dict[str, Any] = {}
        if isinstance(integrations_cfg, dict):
            candidate = integrations_cfg.get("langchain")
            if isinstance(candidate, dict):
                langchain_cfg = candidate
        if not langchain_cfg:
            candidate_root = self._config.get("langchain")
            if isinstance(candidate_root, dict):
                langchain_cfg = candidate_root

        config = LangChainConfig.model_validate(langchain_cfg or {})
        config.validate_semantics()
        self._langchain_adapter = LangChainAdapter(self, config)
        return self._langchain_adapter

    def register_langchain_runnable(
        self,
        *,
        name: str,
        runnable: Any,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        input_transformer: Callable[[dict[str, Any]], Any] | None = None,
        output_transformer: Callable[[Any], Any] | None = None,
        fallback: str | None = None,
        retry_policy: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        enable_tracing: bool = True,
    ) -> None:
        """Register LangChain runnable into capability registry."""
        if not self.registry:
            raise RuntimeError("Must call mount_skills() before registering LangChain runnables")
        adapter = self._get_langchain_adapter()
        from owlclaw.integrations.langchain import RunnableConfig, check_langchain_version

        check_langchain_version()

        adapter.register_runnable(
            runnable=runnable,
            config=RunnableConfig(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                input_transformer=input_transformer,
                output_transformer=output_transformer,
                fallback=fallback,
                retry_policy=retry_policy,
                timeout_seconds=timeout_seconds,
                enable_tracing=enable_tracing,
            ),
        )

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

    def db_change(
        self,
        *,
        channel: str,
        event_name: str | None = None,
        tenant_id: str = "default",
        debounce_seconds: float | None = None,
        batch_size: int | None = None,
        max_buffer_events: int = 1000,
        max_payload_bytes: int = 7900,
        focus: str | None = None,
    ) -> Callable:
        """Decorator to register a db-change trigger with fallback handler."""

        from functools import wraps

        def decorator(fn: Callable) -> Callable:
            cfg = DBChangeTriggerConfig(
                tenant_id=tenant_id,
                channel=channel,
                event_name=event_name or fn.__name__,
                agent_id=self.name,
                debounce_seconds=debounce_seconds,
                batch_size=batch_size,
                max_buffer_events=max_buffer_events,
                max_payload_bytes=max_payload_bytes,
                focus=focus,
            )
            self._ensure_db_change_manager().register(cfg, handler=fn)

            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if inspect.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def api(
        self,
        *,
        path: str,
        method: str = "POST",
        event_name: str | None = None,
        tenant_id: str = "default",
        response_mode: str = "async",
        sync_timeout_seconds: int = 60,
        focus: str | None = None,
        auth_required: bool = True,
        description: str | None = None,
    ) -> Callable:
        """Decorator to register an API trigger endpoint with fallback handler."""

        from functools import wraps

        def decorator(fn: Callable) -> Callable:
            config = APITriggerConfig(
                path=path,
                method=method.upper(),
                event_name=event_name or fn.__name__,
                tenant_id=tenant_id,
                response_mode=response_mode,
                sync_timeout_seconds=sync_timeout_seconds,
                focus=focus,
                auth_required=auth_required,
                description=description or (fn.__doc__ or "").strip() or None,
            )
            self._ensure_api_trigger_server().register(config, fallback=fn)

            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if inspect.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def trigger(self, registration: DBChangeTriggerRegistration | APITriggerRegistration) -> None:
        """Register a trigger using function-call style API."""

        if isinstance(registration, DBChangeTriggerRegistration):
            self._ensure_db_change_manager().register(registration.config)
            return
        if isinstance(registration, APITriggerRegistration):
            self._ensure_api_trigger_server().register(registration.config)
            return
        raise TypeError(f"Unsupported trigger registration type: {type(registration).__name__}")

    def _ensure_db_change_manager(self) -> DBChangeTriggerManager:
        if self.db_change_manager is not None:
            return self.db_change_manager
        dsn = self._resolve_db_change_dsn()
        adapter = PostgresNotifyAdapter(dsn=dsn, reconnect_interval=self._resolve_db_change_reconnect_interval())
        self.db_change_manager = DBChangeTriggerManager(
            adapter=adapter,
            governance=_AllowAllGovernance(),
            agent_runtime=_RuntimeProxy(self),
            ledger=self if self._ledger is not None else None,
        )
        return self.db_change_manager

    def _resolve_db_change_dsn(self) -> str:
        triggers_cfg = self._config.get("triggers", {})
        db_change_cfg: dict[str, Any] = {}
        if isinstance(triggers_cfg, dict):
            candidate = triggers_cfg.get("db_change")
            if isinstance(candidate, dict):
                db_change_cfg = candidate
        dsn = db_change_cfg.get("dsn") or db_change_cfg.get("database_url") or os.getenv("OWLCLAW_DATABASE_URL")
        if not isinstance(dsn, str) or not dsn.strip():
            raise RuntimeError(
                "db_change requires database dsn; set triggers.db_change.dsn or OWLCLAW_DATABASE_URL before registration"
            )
        return dsn.strip()

    def _resolve_db_change_reconnect_interval(self) -> float:
        triggers_cfg = self._config.get("triggers", {})
        if isinstance(triggers_cfg, dict):
            db_change_cfg = triggers_cfg.get("db_change")
            if isinstance(db_change_cfg, dict):
                value = db_change_cfg.get("reconnect_interval", 30.0)
                if isinstance(value, int | float) and value > 0:
                    return float(value)
        return 30.0

    def _ensure_api_trigger_server(self) -> APITriggerServer:
        if self.api_trigger_server is not None:
            return self.api_trigger_server
        config = self._resolve_api_trigger_config()
        auth_provider = self._build_api_auth_provider(config)
        sanitizer = InputSanitizer() if config.get("sanitize_input", True) else None
        governance_gate = _APIGovernanceBridge(self)
        self.api_trigger_server = APITriggerServer(
            host=str(config.get("host", "0.0.0.0")),
            port=int(config.get("port", 8080)),
            auth_provider=auth_provider,
            agent_runtime=_RuntimeProxy(self),
            governance_gate=governance_gate,
            sanitizer=sanitizer,
            ledger=self if self._ledger is not None else None,
            agent_id=self.name,
            max_body_bytes=int(config.get("max_body_bytes", 1024 * 1024)),
            cors_origins=list(config.get("cors_origins", ["*"])),
        )
        return self.api_trigger_server

    def _resolve_api_trigger_config(self) -> dict[str, Any]:
        triggers_cfg = self._config.get("triggers", {})
        if isinstance(triggers_cfg, dict):
            api_cfg = triggers_cfg.get("api")
            if isinstance(api_cfg, dict):
                return dict(api_cfg)
        return {}

    @staticmethod
    def _build_api_auth_provider(config: dict[str, Any]) -> APIKeyAuthProvider | BearerTokenAuthProvider | None:
        auth_type = str(config.get("auth_type", "none")).strip().lower()
        if auth_type == "api_key":
            keys = config.get("api_keys", [])
            if isinstance(keys, list):
                return APIKeyAuthProvider({str(item) for item in keys if str(item).strip()})
            return APIKeyAuthProvider(set())
        if auth_type == "bearer":
            tokens = config.get("bearer_tokens", [])
            if isinstance(tokens, list):
                return BearerTokenAuthProvider({str(item) for item in tokens if str(item).strip()})
            return BearerTokenAuthProvider(set())
        return None

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
        nested_overrides = self._to_nested_overrides(kwargs)
        manager = ConfigManager.load(overrides=nested_overrides)
        self._config = manager.get().model_dump(mode="python")
        triggers_cfg = self._config.get("triggers")
        if isinstance(triggers_cfg, dict):
            self.cron_registry.apply_settings(triggers_cfg)
        governance_cfg = nested_overrides.get("governance")
        if isinstance(governance_cfg, dict):
            self._governance_config = governance_cfg

    @staticmethod
    def _to_nested_overrides(kwargs: dict[str, Any]) -> dict[str, Any]:
        """Convert flat app.configure kwargs into nested config overrides."""
        shortcut_paths = {
            "soul": ("agent", "soul"),
            "identity": ("agent", "identity"),
            "heartbeat_interval_minutes": ("agent", "heartbeat_interval_minutes"),
            "max_iterations": ("agent", "max_iterations"),
            "model": ("integrations", "llm", "model"),
            "temperature": ("integrations", "llm", "temperature"),
            "fallback_models": ("integrations", "llm", "fallback_models"),
        }
        top_level_sections = {
            "agent",
            "governance",
            "triggers",
            "integrations",
            "security",
            "memory",
        }

        nested: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in top_level_sections and isinstance(value, dict):
                current = nested.get(key, {})
                if isinstance(current, dict):
                    current.update(value)
                    nested[key] = current
                else:
                    nested[key] = value
                continue

            path: tuple[str, ...]
            if key in shortcut_paths:
                path = shortcut_paths[key]
            elif "__" in key:
                path = tuple(part.strip().lower() for part in key.split("__") if part.strip())
                if not path:
                    continue
            else:
                path = ("agent", key)

            cursor = nested
            for part in path[:-1]:
                existing = cursor.get(part)
                if not isinstance(existing, dict):
                    existing = {}
                    cursor[part] = existing
                cursor = existing
            cursor[path[-1]] = value
        return nested

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
            if not isinstance(app_dir, str) or not app_dir.strip():
                raise ValueError("app_dir must be a non-empty string when provided")
            resolved_app_dir = app_dir.strip()
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

    async def start(
        self,
        *,
        app_dir: str | None = None,
        hatchet_client: Any = None,
        tenant_id: str = "default",
    ) -> AgentRuntime:
        """Start runtime + governance + cron registration.

        This method keeps `run()` intentionally unimplemented while providing
        an explicit startup path for tests and production bootstrapping.
        """
        runtime = self.create_agent_runtime(app_dir=app_dir, hatchet_client=hatchet_client)
        await runtime.setup()
        await self.start_governance()
        if hatchet_client is not None:
            self.cron_registry.start(
                hatchet_client,
                agent_runtime=runtime,
                ledger=self._ledger,
                tenant_id=tenant_id,
            )
        if self.db_change_manager is not None:
            await self.db_change_manager.start()
        if self.api_trigger_server is not None:
            await self.api_trigger_server.start()
        self._runtime = runtime
        return runtime

    async def stop(self) -> None:
        """Stop governance and wait for cron in-flight tasks."""
        if self.api_trigger_server is not None:
            await self.api_trigger_server.stop()
        if self.db_change_manager is not None:
            await self.db_change_manager.stop()
        await self.stop_governance()
        await self.cron_registry.wait_for_all_tasks()
        self._runtime = None

    def health_status(self) -> dict[str, Any]:
        """Return app-level health summary."""
        return {
            "app": self.name,
            "runtime_initialized": bool(self._runtime and self._runtime.is_initialized),
            "cron": self.cron_registry.get_health_status(),
            "db_change_registered_channels": len(self.db_change_manager._states) if self.db_change_manager else 0,  # noqa: SLF001
            "api_registered_endpoints": len(self.api_trigger_server._configs) if self.api_trigger_server else 0,  # noqa: SLF001
            "governance_enabled": self._ledger is not None,
        }

    def langchain_health_status(self) -> dict[str, Any]:
        """Return LangChain integration health summary."""
        adapter = self._get_langchain_adapter()
        return cast(dict[str, Any], adapter.health_status())

    def langchain_metrics(self, format: str = "json") -> dict[str, Any] | str:
        """Export LangChain metrics in JSON or Prometheus format."""
        adapter = self._get_langchain_adapter()
        return cast(dict[str, Any] | str, adapter.metrics(format=format))

    def run(self) -> None:
        """Start the OwlClaw application.

        Initializes the Agent runtime, loads Skills, starts Hatchet worker,
        and begins processing triggers and heartbeats.
        """
        raise RuntimeError(
            "OwlClaw.run() is not implemented yet. "
            "Use create_agent_runtime() and explicit trigger/worker startup."
        )
