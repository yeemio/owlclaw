"""OwlClaw main application class."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


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

    def mount_skills(self, path: str) -> None:
        """Mount Skills from a business application directory.

        Scans the directory for SKILL.md files following the Agent Skills spec,
        loads their frontmatter metadata, and registers them as capabilities.
        """
        self._skills_path = path

    def handler(self, skill_name: str) -> Callable:
        """Decorator to register a capability handler associated with a Skill.

        The handler function is called when the Agent decides to invoke this capability
        via function calling. The skill_name must match a loaded SKILL.md's `name` field.
        """

        def decorator(fn: Callable) -> Callable:
            self._handlers[skill_name] = fn
            return fn

        return decorator

    def state(self, name: str) -> Callable:
        """Decorator to register a state provider.

        State providers are called by the Agent's query_state built-in tool
        to get current business state snapshots.
        """

        def decorator(fn: Callable) -> Callable:
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
