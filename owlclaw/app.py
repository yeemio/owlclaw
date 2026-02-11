"""OwlClaw main application class."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from owlclaw.capabilities.knowledge import KnowledgeInjector
from owlclaw.capabilities.registry import CapabilityRegistry
from owlclaw.capabilities.skills import SkillsLoader

logger = logging.getLogger(__name__)


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
        """Configure Agent identity, heartbeat, etc.

        Accepts: soul, identity, heartbeat_interval_minutes, and other Agent config.
        """
        self._config.update(kwargs)

    def run(self) -> None:
        """Start the OwlClaw application.

        Initializes the Agent runtime, loads Skills, starts Hatchet worker,
        and begins processing triggers and heartbeats.
        """
        ...
