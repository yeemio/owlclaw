"""Basic tests for capabilities module."""

import pytest
from pathlib import Path
import tempfile
import shutil

from owlclaw.capabilities import Skill, SkillsLoader, CapabilityRegistry, KnowledgeInjector


@pytest.fixture
def temp_capabilities_dir():
    """Create a temporary capabilities directory with test SKILL.md files."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create test Skill 1
    skill1_dir = temp_dir / "test-skill-1"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text("""---
name: test-skill-1
description: Test skill for unit testing
metadata:
  author: test
  version: "1.0"
owlclaw:
  task_type: test_task
  constraints:
    test_only: true
---

# Test Skill 1

This is a test skill for unit testing.

## Usage

Use this skill for testing purposes only.
""")
    
    # Create test Skill 2
    skill2_dir = temp_dir / "test-skill-2"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("""---
name: test-skill-2
description: Another test skill
metadata:
  author: test
  version: "1.0"
---

# Test Skill 2

Another test skill.
""")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_skill_creation():
    """Test Skill object creation."""
    skill = Skill(
        name="test",
        description="Test skill",
        file_path=Path("/tmp/test/SKILL.md"),
        metadata={"author": "test"},
        owlclaw_config={"task_type": "test"},
    )
    
    assert skill.name == "test"
    assert skill.description == "Test skill"
    assert skill.task_type == "test"
    assert skill.constraints == {}


def test_skills_loader_scan(temp_capabilities_dir):
    """Test SkillsLoader scans and loads SKILL.md files."""
    loader = SkillsLoader(temp_capabilities_dir)
    skills = loader.scan()
    
    assert len(skills) == 2
    assert "test-skill-1" in loader.skills
    assert "test-skill-2" in loader.skills


def test_skills_loader_get_skill(temp_capabilities_dir):
    """Test SkillsLoader.get_skill() retrieves Skills by name."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    
    skill = loader.get_skill("test-skill-1")
    assert skill is not None
    assert skill.name == "test-skill-1"
    assert skill.description == "Test skill for unit testing"
    assert skill.task_type == "test_task"


def test_skill_lazy_loading(temp_capabilities_dir):
    """Test Skill full content is loaded lazily."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    
    skill = loader.get_skill("test-skill-1")
    assert skill._is_loaded is False
    
    content = skill.load_full_content()
    assert "Test Skill 1" in content
    assert skill._is_loaded is True
    
    # Second call should return cached content
    content2 = skill.load_full_content()
    assert content == content2


def test_capability_registry_register_handler(temp_capabilities_dir):
    """Test CapabilityRegistry.register_handler()."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    registry = CapabilityRegistry(loader)
    
    def test_handler():
        return "test"
    
    registry.register_handler("test-skill-1", test_handler)
    assert "test-skill-1" in registry.handlers


def test_capability_registry_duplicate_handler(temp_capabilities_dir):
    """Test CapabilityRegistry raises error on duplicate handler registration."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    registry = CapabilityRegistry(loader)
    
    def handler1():
        return "1"
    
    def handler2():
        return "2"
    
    registry.register_handler("test-skill-1", handler1)
    
    with pytest.raises(ValueError, match="already registered"):
        registry.register_handler("test-skill-1", handler2)


@pytest.mark.asyncio
async def test_capability_registry_invoke_handler(temp_capabilities_dir):
    """Test CapabilityRegistry.invoke_handler()."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    registry = CapabilityRegistry(loader)
    
    async def test_handler(value: int):
        return value * 2
    
    registry.register_handler("test-skill-1", test_handler)
    
    result = await registry.invoke_handler("test-skill-1", value=5)
    assert result == 10


def test_knowledge_injector_get_skills_knowledge(temp_capabilities_dir):
    """Test KnowledgeInjector.get_skills_knowledge()."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    injector = KnowledgeInjector(loader)
    
    knowledge = injector.get_skills_knowledge(["test-skill-1", "test-skill-2"])
    
    assert "Available Skills" in knowledge
    assert "test-skill-1" in knowledge
    assert "test-skill-2" in knowledge
    assert "Test Skill 1" in knowledge


def test_knowledge_injector_context_filter(temp_capabilities_dir):
    """Test KnowledgeInjector context filtering."""
    loader = SkillsLoader(temp_capabilities_dir)
    loader.scan()
    injector = KnowledgeInjector(loader)
    
    # Filter to only include skills with test_only constraint
    def filter_test_only(skill):
        return skill.constraints.get("test_only", False)
    
    knowledge = injector.get_skills_knowledge(
        ["test-skill-1", "test-skill-2"],
        context_filter=filter_test_only
    )
    
    assert "test-skill-1" in knowledge
    assert "test-skill-2" not in knowledge
