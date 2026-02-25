"""Skills loading and management for OwlClaw.

This module implements the Skills Loader component, which discovers and loads
SKILL.md files from application directories following the Agent Skills specification.
"""

import logging
import os
import platform
import re
import shutil
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

from owlclaw.capabilities.tool_schema import extract_tools_schema
from owlclaw.config.loader import ConfigLoadError, YAMLConfigLoader

logger = logging.getLogger(__name__)
_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n(.*))?$", re.DOTALL)

if TYPE_CHECKING:
    from owlclaw.capabilities.registry import CapabilityRegistry
    from owlclaw.governance.ledger import Ledger


class Skill:
    """Represents a loaded Skill with metadata and optional full content.

    A Skill is a knowledge document (SKILL.md) that describes a capability's
    purpose, usage guidelines, and relationships with other capabilities.
    Skills follow the Agent Skills open specification (Anthropic, Dec 2025).

    Attributes:
        name: Unique identifier for the Skill
        description: Brief description of what the Skill does
        file_path: Path to the SKILL.md file
        metadata: Agent Skills standard metadata (author, version, tags)
        owlclaw_config: OwlClaw-specific extension fields
    """

    def __init__(
        self,
        name: str,
        description: str,
        file_path: Path,
        metadata: dict[str, Any],
        owlclaw_config: dict[str, Any] | None = None,
        full_content: str | None = None,
    ):
        self.name = name
        self.description = description
        self.file_path = Path(file_path)
        self.metadata = metadata
        self.owlclaw_config = owlclaw_config or {}
        self._full_content = full_content
        self._is_loaded = full_content is not None

    @property
    def task_type(self) -> str | None:
        """Get the task_type for AI routing (OwlClaw extension)."""
        raw = self.owlclaw_config.get("task_type")
        if not isinstance(raw, str):
            return None
        normalized = raw.strip()
        return normalized or None

    @property
    def constraints(self) -> dict[str, Any]:
        """Get the constraints for governance filtering (OwlClaw extension)."""
        raw = self.owlclaw_config.get("constraints", {})
        return raw if isinstance(raw, dict) else {}

    @property
    def trigger(self) -> str | None:
        """Get the trigger configuration (OwlClaw extension)."""
        return self.owlclaw_config.get("trigger")

    @property
    def focus(self) -> list[str]:
        """Get focus tags used for runtime skill selection (OwlClaw extension)."""
        raw = self.owlclaw_config.get("focus", [])
        if isinstance(raw, str):
            normalized = raw.strip()
            return [normalized] if normalized else []
        if isinstance(raw, list | tuple | set):
            out: list[str] = []
            seen: set[str] = set()
            for item in raw:
                if not isinstance(item, str):
                    continue
                normalized = item.strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                out.append(normalized)
            return out
        return []

    @property
    def risk_level(self) -> str:
        """Get declared risk level (low/medium/high/critical), defaulting to low."""
        raw = self.owlclaw_config.get("risk_level", "low")
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"low", "medium", "high", "critical"}:
                return normalized
        return "low"

    @property
    def requires_confirmation(self) -> bool:
        """Whether this skill requires human confirmation before execution.

        For compatibility with architecture v4.1:
        - explicit owlclaw.requires_confirmation takes precedence;
        - high/critical risk defaults to True when not explicitly set.
        """
        raw = self.owlclaw_config.get("requires_confirmation")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, int) and raw in {0, 1}:
            return bool(raw)
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return self.risk_level in {"high", "critical"}

    def load_full_content(self) -> str:
        """Load full instruction text from SKILL.md (lazy loading).

        The full content is loaded only when needed and cached for subsequent
        access. This minimizes memory usage during startup.

        Returns:
            The instruction text (content after frontmatter)
        """
        if not self._is_loaded:
            content = self.file_path.read_text(encoding="utf-8")
            content = content.lstrip("\ufeff")
            match = _FRONTMATTER_PATTERN.match(content)
            self._full_content = (match.group(2) if match else "") or ""
            self._full_content = self._full_content.strip()
            self._is_loaded = True
        return self._full_content or ""

    def clear_full_content_cache(self) -> None:
        """Drop cached full content so subsequent reads re-load from file."""
        self._full_content = None
        self._is_loaded = False

    @property
    def references_dir(self) -> Path | None:
        """Path to references/ directory if it exists.

        The references/ directory contains supporting documentation
        referenced by the Skill (e.g., trading-rules.md).
        """
        ref_dir = self.file_path.parent / "references"
        return ref_dir if ref_dir.exists() else None

    @property
    def scripts_dir(self) -> Path | None:
        """Path to scripts/ directory if it exists.

        The scripts/ directory contains helper scripts used by the Skill
        (e.g., check_signals.py).
        """
        scripts_dir = self.file_path.parent / "scripts"
        return scripts_dir if scripts_dir.exists() else None

    @property
    def assets_dir(self) -> Path | None:
        """Path to assets/ directory if it exists."""
        assets_dir = self.file_path.parent / "assets"
        return assets_dir if assets_dir.exists() else None

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to dict (excludes full content).

        Returns:
            Dictionary with Skill metadata suitable for JSON serialization
        """
        return {
            "name": self.name,
            "description": self.description,
            "file_path": str(self.file_path),
            "metadata": self.metadata,
            "task_type": self.task_type,
            "constraints": self.constraints,
            "trigger": self.trigger,
            "focus": self.focus,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
        }


class SkillsLoader:
    """Discovers and loads SKILL.md files from application directories.

    At startup only frontmatter metadata is loaded; full instruction text
    is loaded on demand via Skill.load_full_content() (progressive loading).
    """

    def __init__(self, base_path: Path | str):
        if isinstance(base_path, str):
            normalized = base_path.strip()
            if not normalized:
                raise ValueError("base_path must be a non-empty path")
            self.base_path = Path(normalized)
        elif isinstance(base_path, Path):
            self.base_path = base_path
        else:
            raise ValueError("base_path must be a non-empty path")
        self.skills: dict[str, Skill] = {}
        self._skills_enabled_overrides: dict[str, bool] = {}

    def scan(self) -> list[Skill]:
        """Recursively scan for SKILL.md files and load metadata.

        Returns:
            List of loaded Skill objects. Invalid or missing files are
            logged and skipped.
        """
        self.skills.clear()
        self._skills_enabled_overrides = self._load_skill_enablement_overrides()
        if not self.base_path.exists() or not self.base_path.is_dir():
            logger.warning("Skills base path does not exist or is not a directory: %s", self.base_path)
            return []
        skill_files = sorted(self.base_path.rglob("SKILL.md"))
        for skill_file in skill_files:
            skill = self._parse_skill_file(skill_file)
            if skill is not None:
                if not self._is_skill_enabled(skill.name):
                    logger.warning("Skill '%s' disabled by config, skipping", skill.name)
                    continue
                if skill.name in self.skills:
                    logger.warning(
                        "Duplicate Skill name '%s' in %s (already loaded from %s); skipping",
                        skill.name,
                        skill_file,
                        self.skills[skill.name].file_path,
                    )
                    continue
                self.skills[skill.name] = skill
        return list(self.skills.values())

    def _parse_skill_file(self, file_path: Path) -> Skill | None:
        """Parse SKILL.md file and extract frontmatter metadata.

        On YAML error, missing required fields, or read error, logs a
        warning and returns None.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to read Skill file %s: %s", file_path, e)
            return None
        content = content.lstrip("\ufeff")

        if not content.startswith("---"):
            logger.warning("Skill file %s missing frontmatter", file_path)
            return None

        match = _FRONTMATTER_PATTERN.match(content)
        if not match:
            logger.warning("Skill file %s invalid frontmatter format", file_path)
            return None
        frontmatter_raw, _body = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
        except yaml.YAMLError as e:
            logger.warning("Skill file %s YAML parse error: %s", file_path, e)
            return None

        if frontmatter is None:
            logger.warning("Skill file %s empty frontmatter", file_path)
            return None
        if not isinstance(frontmatter, dict):
            logger.warning("Skill file %s frontmatter must be a mapping", file_path)
            return None
        frontmatter_map: dict[str, Any] = frontmatter

        if "name" not in frontmatter_map or "description" not in frontmatter_map:
            logger.warning(
                "Skill file %s missing required fields (name, description)",
                file_path,
            )
            return None
        if not isinstance(frontmatter_map["name"], str) or not frontmatter_map["name"].strip():
            logger.warning("Skill file %s invalid name field", file_path)
            return None
        if not _SKILL_NAME_PATTERN.match(frontmatter_map["name"].strip()):
            logger.warning("Skill file %s name must be kebab-case", file_path)
            return None
        if not isinstance(frontmatter_map["description"], str) or not frontmatter_map["description"].strip():
            logger.warning("Skill file %s invalid description field", file_path)
            return None

        metadata = frontmatter_map.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        tools_schema, tool_errors = extract_tools_schema(frontmatter_map)
        if tool_errors:
            for error in tool_errors:
                logger.warning("Skill file %s invalid tool declaration: %s", file_path, error)
        metadata = dict(metadata)
        metadata["tools_schema"] = tools_schema
        owlclaw_config = frontmatter_map.get("owlclaw", {})
        if not isinstance(owlclaw_config, dict):
            owlclaw_config = {}
        prerequisites = self._extract_prerequisites(frontmatter_map, owlclaw_config)
        ready, reasons = self._check_prerequisites(prerequisites)
        if not ready:
            logger.warning(
                "Skill file %s skipped due to unmet prerequisites: %s",
                file_path,
                "; ".join(reasons),
            )
            return None

        return Skill(
            name=frontmatter_map["name"].strip(),
            description=frontmatter_map["description"].strip(),
            file_path=file_path,
            metadata=metadata,
            owlclaw_config=owlclaw_config,
            full_content=None,
        )

    @staticmethod
    def _extract_prerequisites(frontmatter: dict[str, Any], owlclaw_config: dict[str, Any]) -> dict[str, Any]:
        nested = owlclaw_config.get("prerequisites")
        if isinstance(nested, dict):
            return nested
        top_level = frontmatter.get("prerequisites")
        if isinstance(top_level, dict):
            return top_level
        return {}

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if not isinstance(value, list):
            return []
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out

    @staticmethod
    def _get_by_path(data: dict[str, Any], dotted_path: str) -> tuple[bool, Any]:
        if not dotted_path:
            return False, None
        cursor: Any = data
        for part in dotted_path.split("."):
            key = part.strip()
            if not key or not isinstance(cursor, dict) or key not in cursor:
                return False, None
            cursor = cursor[key]
        return True, cursor

    @staticmethod
    def _normalize_os_name(raw: str) -> str:
        candidate = raw.strip().lower()
        aliases = {
            "win32": "windows",
            "windows": "windows",
            "linux": "linux",
            "darwin": "darwin",
            "mac": "darwin",
            "macos": "darwin",
            "osx": "darwin",
        }
        return aliases.get(candidate, candidate)

    def _load_runtime_config(self) -> dict[str, Any]:
        try:
            from owlclaw.config.manager import ConfigManager

            cfg = ConfigManager.instance().get()
            dumped = cfg.model_dump(mode="python")
            return dumped if isinstance(dumped, dict) else {}
        except Exception:
            return {}

    def _load_skill_enablement_overrides(self) -> dict[str, bool]:
        try:
            config_data = YAMLConfigLoader.load_dict()
        except (ConfigLoadError, OSError) as exc:
            logger.warning("Failed to load owlclaw.yaml for skills enablement: %s", exc)
            return {}
        skills_block = config_data.get("skills")
        if not isinstance(skills_block, dict):
            return {}
        entries = skills_block.get("entries")
        if not isinstance(entries, dict):
            return {}
        overrides: dict[str, bool] = {}
        for raw_name, raw_cfg in entries.items():
            if not isinstance(raw_name, str):
                continue
            name = raw_name.strip()
            if not name:
                continue
            if isinstance(raw_cfg, bool):
                overrides[name] = raw_cfg
                continue
            if isinstance(raw_cfg, dict):
                enabled = raw_cfg.get("enabled")
                if isinstance(enabled, bool):
                    overrides[name] = enabled
        return overrides

    def _is_skill_enabled(self, skill_name: str) -> bool:
        return self._skills_enabled_overrides.get(skill_name, True)

    def _check_prerequisites(self, prerequisites: dict[str, Any]) -> tuple[bool, list[str]]:
        if not prerequisites:
            return True, []
        reasons: list[str] = []

        for env_name in self._as_str_list(prerequisites.get("env")):
            if not os.getenv(env_name):
                reasons.append(f"missing env {env_name}")

        for bin_name in self._as_str_list(prerequisites.get("bins")):
            if shutil.which(bin_name) is None:
                reasons.append(f"missing binary {bin_name}")

        for package_name in self._as_str_list(prerequisites.get("python_packages")):
            if find_spec(package_name) is None:
                reasons.append(f"missing python package {package_name}")

        declared_os = {
            self._normalize_os_name(item)
            for item in self._as_str_list(prerequisites.get("os"))
            if self._normalize_os_name(item)
        }
        if declared_os:
            current_os = self._normalize_os_name(platform.system())
            if current_os not in declared_os:
                reasons.append(f"os mismatch {current_os} not in {sorted(declared_os)}")

        cfg_requirements = prerequisites.get("config")
        if isinstance(cfg_requirements, list):
            cfg = self._load_runtime_config()
            for path in self._as_str_list(cfg_requirements):
                found, value = self._get_by_path(cfg, path)
                if not found or value is None:
                    reasons.append(f"missing config {path}")
        elif isinstance(cfg_requirements, dict):
            cfg = self._load_runtime_config()
            for path, expected in cfg_requirements.items():
                if not isinstance(path, str) or not path.strip():
                    continue
                found, value = self._get_by_path(cfg, path.strip())
                if not found:
                    reasons.append(f"missing config {path.strip()}")
                    continue
                if value != expected:
                    reasons.append(f"config mismatch {path.strip()} expected={expected!r} actual={value!r}")

        return len(reasons) == 0, reasons

    def get_skill(self, name: str) -> Skill | None:
        """Retrieve a Skill by name."""
        if not isinstance(name, str):
            return None
        normalized = name.strip()
        if not normalized:
            return None
        return self.skills.get(normalized)

    def list_skills(self) -> list[Skill]:
        """List all loaded Skills."""
        return list(self.skills.values())

    def clear_all_full_content_cache(self) -> int:
        """Clear full content cache for all loaded skills.

        Returns:
            Number of skills whose cache was cleared.
        """
        cleared = 0
        for skill in self.skills.values():
            skill.clear_full_content_cache()
            cleared += 1
        return cleared


def auto_register_binding_tools(
    skills_loader: SkillsLoader,
    registry: "CapabilityRegistry",
    ledger: "Ledger | None" = None,
) -> list[str]:
    """Auto-register binding-declared tools from Skill metadata."""
    from owlclaw.capabilities.bindings import (
        BindingExecutorRegistry,
        BindingTool,
        HTTPBindingExecutor,
        parse_binding_config,
    )

    executor_registry = BindingExecutorRegistry()
    executor_registry.register("http", HTTPBindingExecutor())

    registered: list[str] = []
    for skill in skills_loader.list_skills():
        tools_schema = skill.metadata.get("tools_schema", {})
        if not isinstance(tools_schema, dict):
            continue
        for tool_name, tool_def in tools_schema.items():
            if not isinstance(tool_name, str) or not tool_name.strip() or not isinstance(tool_def, dict):
                continue
            binding_data = tool_def.get("binding")
            if not isinstance(binding_data, dict):
                continue
            if tool_name in registry.handlers:
                continue
            try:
                config = parse_binding_config(binding_data)
            except ValueError as exc:
                logger.warning(
                    "Skip binding tool '%s' in skill '%s': %s",
                    tool_name,
                    skill.name,
                    exc,
                )
                continue
            tool = BindingTool(
                name=tool_name,
                description=str(tool_def.get("description", "")),
                parameters_schema=tool_def.get("parameters", {}) if isinstance(tool_def.get("parameters"), dict) else {},
                binding_config=config,
                executor_registry=executor_registry,
                ledger=ledger,
                risk_level=skill.risk_level,
                requires_confirmation=skill.requires_confirmation,
                task_type=skill.task_type,
                constraints=skill.constraints,
                focus=skill.focus,
            )
            registry.register_handler(tool_name, tool)
            registered.append(tool_name)
    return registered
