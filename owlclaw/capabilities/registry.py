"""Capability registry for managing handlers and state providers.

This module implements the Capability Registry component, which manages
the registration, lookup, and invocation of capability handlers and state
providers.
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any

from owlclaw.capabilities.skills import SkillsLoader

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for capability handlers and state providers.

    The CapabilityRegistry connects Skills (knowledge documents) with their
    corresponding handlers (Python functions). It validates registrations,
    manages lookups, and handles invocations.

    Attributes:
        skills_loader: SkillsLoader instance for Skill metadata access
        handlers: Dictionary mapping Skill names to handler functions
        states: Dictionary mapping state names to provider functions
    """

    def __init__(self, skills_loader: SkillsLoader):
        """Initialize the CapabilityRegistry.

        Args:
            skills_loader: SkillsLoader instance for accessing Skill metadata
        """
        self.skills_loader = skills_loader
        self.handlers: dict[str, Callable] = {}
        self.states: dict[str, Callable] = {}

    def register_handler(self, skill_name: str, handler: Callable) -> None:
        """Register a handler function for a Skill.

        Args:
            skill_name: Name of the Skill this handler implements
            handler: Python function to execute when Skill is invoked

        Raises:
            ValueError: If handler is already registered for this Skill
        """
        # Validate Skill exists (warning only, not blocking)
        skill = self.skills_loader.get_skill(skill_name)
        if not skill:
            logger.warning(
                "Registering handler for non-existent Skill '%s'", skill_name
            )

        # Check for duplicate registration
        if skill_name in self.handlers:
            raise ValueError(
                f"Handler for '{skill_name}' already registered. "
                f"Existing: {self.handlers[skill_name].__name__}, "
                f"New: {handler.__name__}"
            )

        self.handlers[skill_name] = handler

    def register_state(self, state_name: str, provider: Callable) -> None:
        """Register a state provider function.

        Args:
            state_name: Name of the state this provider supplies
            provider: Python function that returns state dict

        Raises:
            TypeError: If provider is not callable
            ValueError: If state provider is already registered
        """
        # Validate provider is callable (sync or async)
        if not callable(provider):
            raise TypeError(
                f"State provider '{state_name}' must be callable"
            )

        # Check for duplicate registration
        if state_name in self.states:
            raise ValueError(
                f"State provider for '{state_name}' already registered"
            )

        self.states[state_name] = provider

    async def invoke_handler(self, skill_name: str, **kwargs) -> Any:
        """Invoke a registered handler by Skill name.

        Args:
            skill_name: Name of the Skill to invoke
            **kwargs: Arguments to pass to the handler

        Returns:
            Result from the handler function

        Raises:
            ValueError: If no handler is registered for the Skill
            RuntimeError: If handler execution fails
        """
        handler = self.handlers.get(skill_name)
        if not handler:
            raise ValueError(
                f"No handler registered for Skill '{skill_name}'"
            )

        try:
            invoke_kwargs = self._prepare_handler_kwargs(handler, kwargs)
            if inspect.iscoroutinefunction(handler):
                return await handler(**invoke_kwargs)
            else:
                return handler(**invoke_kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Handler '{skill_name}' failed: {e}"
            ) from e

    def _prepare_handler_kwargs(
        self,
        handler: Callable,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare invocation kwargs according to handler signature.

        Compatibility rules:
        - If handler accepts ``**kwargs``, pass all arguments through.
        - If handler has no named params, drop all kwargs.
        - If handler has a ``session`` param and caller did not provide it,
          map the full kwargs dict to ``session``.
        - If handler has exactly one named param and no matching key was
          provided, map the full kwargs dict to that parameter.
        - Otherwise, keep only parameters explicitly declared by handler.
        """
        sig = inspect.signature(handler)
        params = sig.parameters

        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return dict(kwargs)

        named_params = {
            name: p
            for name, p in params.items()
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }

        if not named_params:
            return {}

        if "session" in named_params and "session" not in kwargs:
            return {"session": dict(kwargs)}

        filtered = {k: v for k, v in kwargs.items() if k in named_params}
        if filtered:
            return filtered

        if kwargs and len(named_params) == 1:
            param_name = next(iter(named_params))
            return {param_name: dict(kwargs)}

        return filtered

    async def get_state(self, state_name: str) -> dict:
        """Get state from a registered state provider.

        Args:
            state_name: Name of the state to retrieve

        Returns:
            State dictionary from the provider

        Raises:
            ValueError: If no provider is registered for the state
            TypeError: If provider doesn't return a dict
            RuntimeError: If provider execution fails
        """
        provider = self.states.get(state_name)
        if not provider:
            raise ValueError(
                f"No state provider registered for '{state_name}'"
            )

        try:
            if inspect.iscoroutinefunction(provider):
                result = await provider()
            else:
                result = provider()

            if not isinstance(result, dict):
                raise TypeError(
                    f"State provider '{state_name}' must return dict, "
                    f"got {type(result)}"
                )

            return result
        except Exception as e:
            raise RuntimeError(
                f"State provider '{state_name}' failed: {e}"
            ) from e

    def list_capabilities(self) -> list[dict]:
        """List all registered capabilities with metadata.

        Returns:
            List of capability metadata dictionaries
        """
        capabilities = []

        for skill_name, handler in self.handlers.items():
            skill = self.skills_loader.get_skill(skill_name)
            if skill:
                capabilities.append({
                    "name": skill.name,
                    "description": skill.description,
                    "task_type": skill.task_type,
                    "constraints": skill.constraints,
                    "handler": handler.__name__,
                })

        return capabilities

    def get_capability_metadata(self, skill_name: str) -> dict | None:
        """Get metadata for a specific capability.

        Args:
            skill_name: Name of the Skill to query

        Returns:
            Capability metadata dict if found, None otherwise
        """
        skill = self.skills_loader.get_skill(skill_name)
        if not skill:
            return None

        handler = self.handlers.get(skill_name)

        return {
            "name": skill.name,
            "description": skill.description,
            "task_type": skill.task_type,
            "constraints": skill.constraints,
            "handler": handler.__name__ if handler else None,
        }

    def filter_by_task_type(self, task_type: str) -> list[str]:
        """Filter capabilities by task_type.

        Args:
            task_type: Task type to filter by

        Returns:
            List of Skill names matching the task_type
        """
        matching = []

        for skill_name in self.handlers:
            skill = self.skills_loader.get_skill(skill_name)
            if skill and skill.task_type == task_type:
                matching.append(skill_name)

        return matching
