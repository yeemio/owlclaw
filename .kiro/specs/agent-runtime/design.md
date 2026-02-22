# 设计文档

## 文档联动

- requirements: `.kiro/specs/agent-runtime/requirements.md`
- design: `.kiro/specs/agent-runtime/design.md`
- tasks: `.kiro/specs/agent-runtime/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 简介

本文档描述了 OwlClaw Agent 运行时核心模块的技术设计。Agent 运行时是 OwlClaw 的心脏，负责将 Agent 从无状态函数转变为**有身份、有记忆、有知识的持续实体**。

核心设计理念：

> **不要控制 Agent，赋能 Agent。**

Agent 通过 LLM function calling 自主决定何时使用哪些能力，而不是由外部循环控制。Agent 运行时提供：

1. **身份系统** — SOUL.md（角色定位）+ IDENTITY.md（能力范围）
2. **记忆系统** — 短期记忆（当前 run）+ 长期记忆（MEMORY.md + 向量搜索）
3. **知识系统** — Skills 的 SKILL.md 注入到 system prompt
4. **决策系统** — LLM function calling 从可见工具中选择动作
5. **Heartbeat 机制** — 无事不调 LLM，节省成本

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Runtime                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  1. Identity Loader                                         │    │
│  │     ├─ Load SOUL.md (role & principles)                     │    │
│  │     └─ Load IDENTITY.md (capabilities & constraints)        │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  2. Memory System                                           │    │
│  │     ├─ Short-term: Current run context                      │    │
│  │     └─ Long-term: MEMORY.md + Vector search                 │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  3. Knowledge Injector                                      │    │
│  │     ├─ Load Skills metadata (startup)                       │    │
│  │     ├─ Select relevant Skills (per run)                     │    │
│  │     └─ Inject SKILL.md to system prompt                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  4. Decision Loop (Function Calling)                        │    │
│  │     ├─ Build visible tools list (governance filtered)       │    │
│  │     ├─ Construct system prompt (identity + memory + skills) │    │
│  │     ├─ Call LLM with function calling                       │    │
│  │     ├─ Execute tool calls                                   │    │
│  │     └─ Repeat until LLM completes                           │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  5. Heartbeat Checker                                       │    │
│  │     ├─ Check for pending events                             │    │
│  │     ├─ Skip LLM if no events                                │    │
│  │     └─ Start full run if events exist                       │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      External Integrations                           │
│                                                                      │
│  Hatchet (持久执行) · litellm (LLM) · Langfuse (追踪)                │
│  Built-in Tools · Capability Registry · Governance Layer             │
└─────────────────────────────────────────────────────────────────────┘
```


## 组件设计

### 1. AgentRuntime 类

**职责：** Agent 运行时的主入口，协调所有子系统，管理 Agent Run 的完整生命周期。

#### 1.1 类定义

```python
from typing import Optional, Any
from dataclasses import dataclass
import asyncio

@dataclass
class AgentRunContext:
    """Context for a single Agent run."""
    agent_id: str
    run_id: str
    trigger: str  # "cron", "schedule_once", "webhook", "heartbeat", etc.
    payload: dict
    focus: Optional[str] = None  # From schedule_once/schedule_cron
    tenant_id: str = "default"

class AgentRuntime:
    """
    Agent Runtime - Core orchestrator for Agent execution.
    
    Responsibilities:
    - Load Agent identity (SOUL.md, IDENTITY.md)
    - Manage memory (short-term + long-term)
    - Inject knowledge (Skills)
    - Execute decision loop (LLM function calling)
    - Handle heartbeat checks
    """
    
    def __init__(
        self,
        agent_id: str,
        app_dir: str,
        hatchet_client,
        llm_client,
        langfuse_client,
        capability_registry,
        governance_layer,
        built_in_tools,
        vector_db,
        config: dict,
    ):
        self.agent_id = agent_id
        self.app_dir = app_dir
        self.config = config
        
        # External integrations
        self.hatchet = hatchet_client
        self.llm = llm_client
        self.langfuse = langfuse_client
        self.registry = capability_registry
        self.governance = governance_layer
        self.tools = built_in_tools
        self.vector_db = vector_db
        
        # Sub-systems (initialized in setup())
        self.identity_loader = None
        self.memory_system = None
        self.knowledge_injector = None
        self.heartbeat_checker = None
        
        # Runtime state
        self.is_initialized = False
    
    async def setup(self):
        """
        Initialize Agent Runtime.
        
        Loads identity, sets up memory system, loads Skills metadata.
        """
        # 1. Load identity
        self.identity_loader = IdentityLoader(self.app_dir)
        await self.identity_loader.load()
        
        # 2. Setup memory system
        self.memory_system = MemorySystem(
            agent_id=self.agent_id,
            app_dir=self.app_dir,
            vector_db=self.vector_db,
            config=self.config.get("memory", {}),
        )
        await self.memory_system.setup()
        
        # 3. Setup knowledge injector
        self.knowledge_injector = KnowledgeInjector(
            app_dir=self.app_dir,
            capability_registry=self.registry,
            config=self.config.get("knowledge", {}),
        )
        await self.knowledge_injector.load_skills_metadata()
        
        # 4. Setup heartbeat checker
        self.heartbeat_checker = HeartbeatChecker(
            agent_id=self.agent_id,
            config=self.config.get("heartbeat", {}),
        )
        
        self.is_initialized = True
    
    async def run(self, context: AgentRunContext) -> dict:
        """
        Execute a single Agent run.
        
        Args:
            context: Agent run context (trigger, payload, focus, etc.)
        
        Returns:
            Run result summary
        """
        if not self.is_initialized:
            raise RuntimeError("AgentRuntime not initialized. Call setup() first.")
        
        # Start Langfuse trace
        trace = self.langfuse.trace(
            name=f"agent_run_{context.run_id}",
            metadata={
                "agent_id": context.agent_id,
                "trigger": context.trigger,
                "focus": context.focus,
            },
        )
        
        try:
            # Heartbeat check (skip LLM if no events)
            if context.trigger == "heartbeat":
                has_events = await self.heartbeat_checker.check_events()
                if not has_events:
                    return {"status": "skipped", "reason": "no_events"}
            
            # Execute decision loop
            result = await self._decision_loop(context, trace)
            
            return {"status": "completed", "result": result}
        
        except Exception as e:
            trace.event(name="error", metadata={"error": str(e)})
            raise
        
        finally:
            trace.end()
    
    async def _decision_loop(self, context: AgentRunContext, trace) -> dict:
        """
        Core decision loop: LLM function calling until completion.
        """
        # 1. Build short-term memory
        short_term_memory = await self.memory_system.build_short_term_context(context)
        
        # 2. Recall relevant long-term memory
        long_term_memory = await self.memory_system.recall_relevant(context)
        
        # 3. Select and inject relevant Skills
        skills_context = await self.knowledge_injector.select_skills(context)
        
        # 4. Build visible tools list (governance filtered)
        visible_tools = await self.governance.filter_visible_tools(
            agent_id=context.agent_id,
            all_tools=self._get_all_tools(),
            context=context,
        )
        
        # 5. Construct system prompt
        system_prompt = self._build_system_prompt(
            identity=self.identity_loader.get_identity(),
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            skills_context=skills_context,
            visible_tools=visible_tools,
        )
        
        # 6. LLM function calling loop
        messages = [{"role": "system", "content": system_prompt}]
        
        if context.focus:
            messages.append({
                "role": "user",
                "content": f"Focus: {context.focus}"
            })
        
        max_iterations = self.config.get("max_function_calls", 50)
        
        for iteration in range(max_iterations):
            # Call LLM
            response = await self.llm.chat_completion(
                messages=messages,
                tools=visible_tools,
                trace=trace,
            )
            
            # Check if LLM wants to call a function
            if not response.get("tool_calls"):
                # LLM finished
                break
            
            # Execute tool calls
            for tool_call in response["tool_calls"]:
                tool_result = await self._execute_tool(
                    tool_call=tool_call,
                    context=context,
                    trace=trace,
                )
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(tool_result),
                })
        
        return {"iterations": iteration + 1, "final_response": response}
    
    def _get_all_tools(self) -> list[dict]:
        """Get all available tools (built-in + business capabilities)."""
        tools = []
        
        # Built-in tools
        tools.extend(self.tools.get_tool_schemas())
        
        # Business capabilities
        tools.extend(self.registry.get_capability_schemas())
        
        return tools
    
    async def _execute_tool(
        self,
        tool_call: dict,
        context: AgentRunContext,
        trace,
    ) -> Any:
        """Execute a tool call (built-in or business capability)."""
        tool_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]
        
        span = trace.span(name=f"tool_{tool_name}")
        
        try:
            # Check if built-in tool
            if tool_name in self.tools.get_tool_names():
                result = await self.tools.execute(
                    tool_name=tool_name,
                    arguments=arguments,
                    context=context.__dict__,
                )
            else:
                # Business capability
                result = await self.registry.execute_capability(
                    capability_name=tool_name,
                    arguments=arguments,
                    context=context.__dict__,
                )
            
            span.event(name="success", metadata={"result": result})
            return result
        
        except Exception as e:
            span.event(name="error", metadata={"error": str(e)})
            return {"error": str(e)}
        
        finally:
            span.end()
    
    def _build_system_prompt(
        self,
        identity: dict,
        short_term_memory: str,
        long_term_memory: list[dict],
        skills_context: str,
        visible_tools: list[dict],
    ) -> str:
        """Construct system prompt from all context."""
        prompt_parts = []
        
        # 1. Identity (SOUL.md)
        prompt_parts.append("# Your Identity\n")
        prompt_parts.append(identity["soul"])
        
        # 2. Capabilities (IDENTITY.md summary)
        prompt_parts.append("\n# Your Capabilities\n")
        prompt_parts.append(identity["capabilities_summary"])
        
        # 3. Long-term memory (if any)
        if long_term_memory:
            prompt_parts.append("\n# Relevant Past Experiences\n")
            for memory in long_term_memory:
                prompt_parts.append(f"- {memory['content']} (tags: {', '.join(memory['tags'])})\n")
        
        # 4. Skills knowledge
        if skills_context:
            prompt_parts.append("\n# Business Knowledge\n")
            prompt_parts.append(skills_context)
        
        # 5. Short-term memory
        if short_term_memory:
            prompt_parts.append("\n# Current Context\n")
            prompt_parts.append(short_term_memory)
        
        # 6. Available tools
        prompt_parts.append("\n# Available Tools\n")
        prompt_parts.append(f"You have access to {len(visible_tools)} tools. ")
        prompt_parts.append("Use function calling to choose actions.\n")
        
        return "".join(prompt_parts)
```


### 2. IdentityLoader 类

**职责：** 加载和管理 Agent 的身份定义（SOUL.md 和 IDENTITY.md）。

```python
import os
from pathlib import Path

class IdentityLoader:
    """
    Load and manage Agent identity from SOUL.md and IDENTITY.md.
    """
    
    def __init__(self, app_dir: str):
        self.app_dir = Path(app_dir)
        self.soul_path = self.app_dir / "SOUL.md"
        self.identity_path = self.app_dir / "IDENTITY.md"
        
        self.soul_content = None
        self.identity_content = None
    
    async def load(self):
        """Load SOUL.md and IDENTITY.md."""
        # Load SOUL.md
        if not self.soul_path.exists():
            raise FileNotFoundError(f"SOUL.md not found at {self.soul_path}")
        
        with open(self.soul_path, "r", encoding="utf-8") as f:
            self.soul_content = f.read()
        
        # Load IDENTITY.md
        if not self.identity_path.exists():
            raise FileNotFoundError(f"IDENTITY.md not found at {self.identity_path}")
        
        with open(self.identity_path, "r", encoding="utf-8") as f:
            self.identity_content = f.read()
    
    def get_identity(self) -> dict:
        """
        Get Agent identity for system prompt.
        
        Returns:
            {
                "soul": str,  # Full SOUL.md content
                "capabilities_summary": str,  # Summary from IDENTITY.md
            }
        """
        return {
            "soul": self.soul_content,
            "capabilities_summary": self._extract_capabilities_summary(),
        }
    
    def _extract_capabilities_summary(self) -> str:
        """
        Extract capabilities summary from IDENTITY.md.
        
        Parses the "## My Capabilities" section.
        """
        # Simple parsing: extract lines between "## My Capabilities" and next "##"
        lines = self.identity_content.split("\n")
        in_capabilities = False
        summary_lines = []
        
        for line in lines:
            if line.startswith("## My Capabilities") or line.startswith("## 我的能力"):
                in_capabilities = True
                continue
            
            if in_capabilities:
                if line.startswith("##"):
                    break
                summary_lines.append(line)
        
        return "\n".join(summary_lines).strip()
    
    async def reload(self):
        """Reload identity files (hot reload)."""
        await self.load()
```

### 3. MemorySystem 类

**职责：** 管理 Agent 的短期记忆和长期记忆。

```python
from typing import Optional
from datetime import datetime
import json

class MemorySystem:
    """
    Manage Agent memory: short-term (current run) + long-term (MEMORY.md + vector search).
    """
    
    def __init__(
        self,
        agent_id: str,
        app_dir: str,
        vector_db,
        config: dict,
    ):
        self.agent_id = agent_id
        self.app_dir = Path(app_dir)
        self.memory_path = self.app_dir / "MEMORY.md"
        self.vector_db = vector_db
        self.config = config
        
        # Short-term memory (current run)
        self.short_term = []
        
        # Long-term memory cache
        self.long_term_cache = []
    
    async def setup(self):
        """Initialize memory system."""
        # Create MEMORY.md if not exists
        if not self.memory_path.exists():
            self.memory_path.write_text("# Agent Memory\n\n", encoding="utf-8")
        
        # Load existing memories into vector DB (if not already indexed)
        await self._index_existing_memories()
    
    async def build_short_term_context(self, context: AgentRunContext) -> str:
        """
        Build short-term memory context for current run.
        
        Includes:
        - Trigger information
        - Focus (if from schedule)
        - Recent tool calls (this run)
        """
        parts = []
        
        parts.append(f"Trigger: {context.trigger}")
        
        if context.focus:
            parts.append(f"Focus: {context.focus}")
        
        if context.payload:
            parts.append(f"Payload: {json.dumps(context.payload, indent=2)}")
        
        if self.short_term:
            parts.append("\nRecent actions:")
            for action in self.short_term[-5:]:  # Last 5 actions
                parts.append(f"- {action}")
        
        return "\n".join(parts)
    
    def add_short_term(self, action: str):
        """Add action to short-term memory."""
        self.short_term.append(action)
        
        # Limit short-term memory size
        max_size = self.config.get("short_term_max_size", 20)
        if len(self.short_term) > max_size:
            self.short_term = self.short_term[-max_size:]
    
    async def recall_relevant(
        self,
        context: AgentRunContext,
        limit: int = 5,
    ) -> list[dict]:
        """
        Recall relevant long-term memories for current context.
        
        Uses vector search based on context.focus or context.trigger.
        """
        if not context.focus:
            return []
        
        # Vector search
        results = await self.vector_db.search(
            collection=f"agent_memory_{self.agent_id}",
            query=context.focus,
            limit=limit,
        )
        
        return results
    
    async def write(
        self,
        content: str,
        tags: list[str],
        run_id: str,
    ) -> str:
        """
        Write to long-term memory (MEMORY.md + vector DB).
        
        Returns memory_id.
        """
        timestamp = datetime.utcnow().isoformat()
        memory_id = f"mem_{timestamp}_{run_id[:8]}"
        
        # Append to MEMORY.md
        entry = f"\n## {memory_id}\n"
        entry += f"**Time:** {timestamp}\n"
        entry += f"**Tags:** {', '.join(tags)}\n"
        entry += f"**Content:** {content}\n"
        
        with open(self.memory_path, "a", encoding="utf-8") as f:
            f.write(entry)
        
        # Index to vector DB
        await self.vector_db.insert(
            collection=f"agent_memory_{self.agent_id}",
            id=memory_id,
            text=content,
            metadata={
                "timestamp": timestamp,
                "tags": tags,
                "run_id": run_id,
            },
        )
        
        return memory_id
    
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search long-term memory by query.
        
        Returns list of memories with content, tags, timestamp.
        """
        results = await self.vector_db.search(
            collection=f"agent_memory_{self.agent_id}",
            query=query,
            limit=limit,
        )
        
        return results
    
    async def _index_existing_memories(self):
        """Index existing MEMORY.md entries to vector DB."""
        # Parse MEMORY.md and index entries
        # (Implementation details omitted for brevity)
        pass
```


### 4. KnowledgeInjector 类

**职责：** 加载和注入 Skills 知识文档到 system prompt。

```python
import yaml
from pathlib import Path

class KnowledgeInjector:
    """
    Load and inject Skills knowledge (SKILL.md) into system prompt.
    
    Follows Agent Skills specification (agentskills.io).
    """
    
    def __init__(
        self,
        app_dir: str,
        capability_registry,
        config: dict,
    ):
        self.app_dir = Path(app_dir)
        self.registry = capability_registry
        self.config = config
        
        # Skills metadata cache (loaded at startup)
        self.skills_metadata = {}
        
        # Skills full content cache (loaded on demand)
        self.skills_content = {}
    
    async def load_skills_metadata(self):
        """
        Load Skills metadata (frontmatter only) for all capabilities.
        
        Progressive loading: metadata at startup, full content on demand.
        """
        capabilities = self.registry.get_all_capabilities()
        
        for cap in capabilities:
            skill_path = self.app_dir / "capabilities" / cap["name"] / "SKILL.md"
            
            if not skill_path.exists():
                continue
            
            # Parse frontmatter
            metadata = self._parse_skill_frontmatter(skill_path)
            self.skills_metadata[cap["name"]] = metadata
    
    def _parse_skill_frontmatter(self, skill_path: Path) -> dict:
        """
        Parse SKILL.md frontmatter (YAML).
        
        Returns metadata dict.
        """
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract YAML frontmatter between --- markers
        if not content.startswith("---"):
            return {}
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        
        frontmatter = parts[1]
        metadata = yaml.safe_load(frontmatter)
        
        return metadata
    
    async def select_skills(self, context: AgentRunContext) -> str:
        """
        Select relevant Skills for current context and load full content.
        
        Selection strategy:
        1. If context.focus matches a capability name, load that Skill
        2. Otherwise, load Skills based on trigger type
        3. Limit total tokens to max_skills_tokens
        
        Returns concatenated Skills content for system prompt.
        """
        selected_skills = []
        
        # Strategy 1: Focus-based selection
        if context.focus:
            for skill_name, metadata in self.skills_metadata.items():
                if skill_name in context.focus.lower():
                    selected_skills.append(skill_name)
        
        # Strategy 2: Trigger-based selection
        if not selected_skills:
            # Load all Skills (for MVP, can be optimized later)
            selected_skills = list(self.skills_metadata.keys())
        
        # Load full content
        skills_content_parts = []
        total_tokens = 0
        max_tokens = self.config.get("max_skills_tokens", 4000)
        
        for skill_name in selected_skills:
            content = await self._load_skill_content(skill_name)
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(content) // 4
            
            if total_tokens + estimated_tokens > max_tokens:
                break
            
            skills_content_parts.append(f"## Skill: {skill_name}\n{content}\n")
            total_tokens += estimated_tokens
        
        return "\n".join(skills_content_parts)
    
    async def _load_skill_content(self, skill_name: str) -> str:
        """
        Load full SKILL.md content (excluding frontmatter).
        
        Caches content after first load.
        """
        if skill_name in self.skills_content:
            return self.skills_content[skill_name]
        
        skill_path = self.app_dir / "capabilities" / skill_name / "SKILL.md"
        
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        
        self.skills_content[skill_name] = content
        return content
```

### 5. HeartbeatChecker 类

**职责：** 检查是否有待处理事件，决定是否需要调用 LLM。

```python
class HeartbeatChecker:
    """
    Check for pending events to decide if LLM call is needed.
    
    Heartbeat mechanism: no events = skip LLM, save cost.
    """
    
    def __init__(self, agent_id: str, config: dict):
        self.agent_id = agent_id
        self.config = config
        
        # Event sources to check (configurable)
        self.event_sources = config.get("event_sources", [
            "webhook",
            "queue",
            "database",
            "schedule",
        ])
    
    async def check_events(self) -> bool:
        """
        Check if there are pending events.
        
        Returns True if events exist, False otherwise.
        """
        for source in self.event_sources:
            if await self._check_source(source):
                return True
        
        return False
    
    async def _check_source(self, source: str) -> bool:
        """
        Check a specific event source.
        
        Returns True if events exist in this source.
        """
        if source == "webhook":
            return await self._check_webhook_events()
        elif source == "queue":
            return await self._check_queue_events()
        elif source == "database":
            return await self._check_database_events()
        elif source == "schedule":
            return await self._check_schedule_events()
        else:
            return False
    
    async def _check_webhook_events(self) -> bool:
        """Check for new webhook events."""
        # Query database for unprocessed webhook events
        # (Implementation depends on webhook storage)
        return False
    
    async def _check_queue_events(self) -> bool:
        """Check for new queue messages."""
        # Query message queue for pending messages
        # (Implementation depends on queue system)
        return False
    
    async def _check_database_events(self) -> bool:
        """Check for database change events."""
        # Query database for change notifications
        # (Implementation depends on database triggers)
        return False
    
    async def _check_schedule_events(self) -> bool:
        """Check for due scheduled tasks."""
        # Query Hatchet for due tasks
        # (Implementation depends on Hatchet API)
        return False
```


## 数据模型

### Agent Run Context

```python
@dataclass
class AgentRunContext:
    """Context for a single Agent run."""
    agent_id: str                    # Agent identifier (e.g., "mionyee-trading")
    run_id: str                      # Unique run ID (e.g., "run_20260210_173000_abc123")
    trigger: str                     # Trigger type: "cron", "schedule_once", "webhook", "heartbeat"
    payload: dict                    # Trigger-specific payload
    focus: Optional[str] = None      # Focus from schedule_once/schedule_cron
    tenant_id: str = "default"       # Tenant ID (for multi-tenancy)
```

### Identity Structure

```python
{
    "soul": str,                     # Full SOUL.md content
    "capabilities_summary": str,     # Extracted from IDENTITY.md
}
```

### Memory Entry

```python
{
    "memory_id": str,                # e.g., "mem_2026-02-10T17:30:00_abc123"
    "agent_id": str,
    "content": str,                  # Memory content (max 2000 chars)
    "tags": list[str],               # Tags for categorization
    "timestamp": str,                # ISO 8601 timestamp
    "run_id": str,                   # Run that created this memory
    "embedding": list[float],        # Vector representation
}
```

### Skill Metadata

```python
{
    "name": str,                     # Skill name (e.g., "entry-monitor")
    "description": str,              # Short description
    "metadata": {
        "author": str,
        "version": str,
    },
    "owlclaw": {                     # OwlClaw extensions
        "task_type": str,            # For AI routing
        "constraints": dict,         # Visibility constraints
    },
}
```

### Run Result

```python
{
    "status": str,                   # "completed", "failed", "skipped"
    "iterations": int,               # Number of LLM function calling iterations
    "final_response": dict,          # Final LLM response
    "tools_called": list[str],       # List of tools called
    "duration_ms": int,              # Total run duration
    "tokens_used": int,              # Total tokens used
}
```

## 接口设计

### AgentRuntime 公共接口

```python
class AgentRuntime:
    async def setup() -> None:
        """Initialize Agent Runtime (load identity, setup memory, load Skills)."""
    
    async def run(context: AgentRunContext) -> dict:
        """Execute a single Agent run."""
    
    async def reload_identity() -> None:
        """Hot reload SOUL.md and IDENTITY.md."""
    
    async def reload_skills() -> None:
        """Hot reload Skills metadata."""
    
    def get_status() -> dict:
        """Get runtime status (initialized, memory size, skills count, etc.)."""
```

### MemorySystem 公共接口

```python
class MemorySystem:
    async def setup() -> None:
        """Initialize memory system."""
    
    async def write(content: str, tags: list[str], run_id: str) -> str:
        """Write to long-term memory. Returns memory_id."""
    
    async def search(query: str, limit: int = 5) -> list[dict]:
        """Search long-term memory. Returns list of memories."""
    
    async def recall_relevant(context: AgentRunContext, limit: int = 5) -> list[dict]:
        """Recall relevant memories for current context."""
    
    def add_short_term(action: str) -> None:
        """Add action to short-term memory."""
```

### KnowledgeInjector 公共接口

```python
class KnowledgeInjector:
    async def load_skills_metadata() -> None:
        """Load Skills metadata (frontmatter only)."""
    
    async def select_skills(context: AgentRunContext) -> str:
        """Select and load relevant Skills for current context."""
    
    async def reload_skills() -> None:
        """Hot reload Skills metadata and clear content cache."""
```

### HeartbeatChecker 公共接口

```python
class HeartbeatChecker:
    async def check_events() -> bool:
        """Check if there are pending events. Returns True if events exist."""
```


## 正确性属性

*属性（Property）是关于系统行为的形式化陈述，应该在所有有效执行中保持为真。属性是人类可读规范和机器可验证正确性保证之间的桥梁。每个属性都是一个通用量化的陈述，可以通过基于属性的测试（Property-Based Testing）在大量生成的输入上进行验证。*

### Property Reflection

在编写属性之前，我们需要识别并消除冗余：

**分析结果：**
- 属性 1.1 和 1.2（加载 SOUL.md 和 IDENTITY.md）可以合并为一个属性：身份文件加载
- 属性 1.3 和 1.4（验证文件存在和返回错误）是同一个行为的两个方面，可以合并
- 属性 2.6 和 2.7（token 限制和自动压缩）是相关的，但测试不同的行为，保持独立
- 属性 3.2 和 3.3（写入 MEMORY.md 和生成 embedding）是 remember 工具的两个方面，可以合并为一个综合属性
- 属性 5.8 和 5.9（function call 限制和终止）是同一个行为，可以合并
- 属性 7.4 和 7.5（heartbeat 跳过和触发）是互补的，但测试不同的分支，保持独立
- 属性 12.1 和 1.4 是重复的，删除 12.1
- 属性 16.1 和 16.3（sanitization）可以合并为一个综合的输入清理属性

**最终属性列表：**
1. 身份文件加载完整性
2. 身份文件缺失错误处理
3. 身份热重载一致性
4. 短期记忆 token 限制
5. 短期记忆自动压缩
6. 长期记忆写入完整性（round-trip）
7. 长期记忆向量搜索相关性
8. MEMORY.md 文件大小限制
9. Skills 格式验证
10. Skills token 限制
11. Function calling 次数限制
12. LLM 调用超时控制
13. 工具可见性过滤日志
14. Heartbeat 无事件优化
15. Heartbeat 有事件触发
16. Agent Run 超时控制
17. Hatchet 任务重试
18. Token 使用量记录
19. Langfuse trace 创建
20. 向量数据库降级
21. 工具错误传播
22. 配置验证
23. 输入内容清理

### 属性定义

**Property 1: 身份文件加载完整性**

*对于任何* 包含有效 SOUL.md 和 IDENTITY.md 的应用目录，Agent Runtime 初始化应该成功，并且加载的内容应该在 system prompt 中可用。

**验证：需求 1.1, 1.2, 1.7, 1.8**

---

**Property 2: 身份文件缺失错误处理**

*对于任何* 缺少 SOUL.md 或 IDENTITY.md 的应用目录，Agent Runtime 初始化应该失败并返回明确的错误信息。

**验证：需求 1.3, 1.4**

---

**Property 3: 身份热重载一致性**

*对于任何* 已初始化的 Agent Runtime，修改 SOUL.md 或 IDENTITY.md 后调用 reload()，后续 Agent Run 应该使用新的内容。

**验证：需求 1.9**

---

**Property 4: 短期记忆 token 限制**

*对于任何* 短期记忆内容，构建的上下文字符串的 token 数量应该不超过配置的限制（默认 2000 tokens）。

**验证：需求 2.6**

---

**Property 5: 短期记忆自动压缩**

*对于任何* 超过 token 限制的短期记忆内容，系统应该自动压缩，压缩后的内容应该在限制内且保留最重要的信息。

**验证：需求 2.7**

---

**Property 6: 长期记忆写入完整性（Round-trip）**

*对于任何* 有效的记忆内容和标签，调用 remember 工具后，该内容应该被写入 MEMORY.md 并索引到向量数据库，后续调用 recall 应该能够检索到该记忆。

**验证：需求 3.2, 3.3, 3.4**

---

**Property 7: 长期记忆向量搜索相关性**

*对于任何* recall 查询，返回的记忆应该与查询语义相关，并且按相关性和时间衰减排序。

**验证：需求 3.5, 3.6**

---

**Property 8: MEMORY.md 文件大小限制**

*对于任何* Agent 实例，当 MEMORY.md 文件大小接近配置的限制（默认 10MB）时，系统应该触发自动归档，归档后文件大小应该在限制内。

**验证：需求 3.8, 3.9**

---

**Property 9: Skills 格式验证**

*对于任何* SKILL.md 文件，如果 frontmatter 格式有效（YAML + owlclaw 扩展字段），系统应该成功加载；如果格式无效，系统应该记录警告并跳过该 Skill。

**验证：需求 4.1, 4.11**

---

**Property 10: Skills token 限制**

*对于任何* Agent Run，注入到 system prompt 的 Skills 内容的总 token 数量应该不超过配置的限制（默认 4000 tokens）。

**验证：需求 4.8**

---

**Property 11: Function calling 次数限制**

*对于任何* Agent Run，LLM function calling 的迭代次数应该不超过配置的限制（默认 50 次），超过限制时应该终止 run 并记录警告。

**验证：需求 5.8, 5.9**

---

**Property 12: LLM 调用超时控制**

*对于任何* LLM 调用，如果执行时间超过配置的超时（默认 60 秒），系统应该终止调用并返回超时错误。

**验证：需求 5.12, 5.13**

---

**Property 13: 工具可见性过滤日志**

*对于任何* 工具可见性过滤决策，系统应该在 Ledger 中记录过滤的原因和结果。

**验证：需求 6.11**

---

**Property 14: Heartbeat 无事件优化**

*对于任何* Heartbeat 触发的 Agent Run，如果没有待处理事件，系统应该跳过 LLM 调用并直接结束 run，run 状态应该为 "skipped"。

**验证：需求 7.4**

---

**Property 15: Heartbeat 有事件触发**

*对于任何* Heartbeat 触发的 Agent Run，如果有待处理事件，系统应该启动完整的 Agent Run（包括 LLM 调用）。

**验证：需求 7.5**

---

**Property 16: Agent Run 超时控制**

*对于任何* Agent Run，如果总执行时间超过配置的超时（默认 5 分钟），系统应该自动终止并记录超时错误。

**验证：需求 8.8, 8.9**

---

**Property 17: Hatchet 任务重试**

*对于任何* 失败的 Hatchet 任务，系统应该根据配置的重试策略自动重试，重试次数应该不超过配置的最大值。

**验证：需求 9.7**

---

**Property 18: Token 使用量记录**

*对于任何* LLM 调用，系统应该在 Ledger 中记录 token 使用量（prompt tokens + completion tokens）。

**验证：需求 10.9**

---

**Property 19: Langfuse trace 创建**

*对于任何* Agent Run，系统应该创建对应的 Langfuse trace，trace 应该包含 Agent 身份、触发信息和所有 LLM 调用的 span。

**验证：需求 11.2, 11.3, 11.4**

---

**Property 20: 向量数据库降级**

*对于任何* Agent Run，如果向量数据库连接失败，系统应该降级到仅使用 MEMORY.md，recall 工具应该返回空结果而不是错误。

**验证：需求 12.3**

---

**Property 21: 工具错误传播**

*对于任何* 工具执行失败，系统应该将错误信息（而不是异常）返回给 LLM，LLM 应该能够基于错误信息做出后续决策。

**验证：需求 12.5**

---

**Property 22: 配置验证**

*对于任何* 配置文件，如果包含无效的配置项（如负数超时、无效的 cron 表达式），系统应该在启动时拒绝该配置并返回验证错误。

**验证：需求 14.11**

---

**Property 23: 输入内容清理**

*对于任何* 从文件加载的内容（SOUL.md、IDENTITY.md、SKILL.md），系统应该进行 sanitization，移除或转义潜在的恶意内容（如 prompt injection 尝试）。

**验证：需求 16.1, 16.2, 16.3**


## 错误处理

### 1. 初始化错误

**场景：** SOUL.md 或 IDENTITY.md 不存在

```python
FileNotFoundError: SOUL.md not found at /path/to/app/SOUL.md
```

**处理：** 抛出异常，阻止 Agent Runtime 初始化

---

**场景：** SKILL.md frontmatter 格式错误

```python
# 行为：记录警告，跳过该 Skill，继续初始化

WARNING: Invalid SKILL.md frontmatter in entry-monitor: 
  yaml.scanner.ScannerError: mapping values are not allowed here
```

**处理：** 记录警告到日志，该 Skill 不可用，但不影响其他 Skills

---

### 2. 运行时错误

**场景：** LLM 调用失败

```python
# 行为：根据重试策略重试，或降级到备用模型

RuntimeError: LLM call failed: 
  litellm.RateLimitError: Rate limit exceeded for gpt-4
```

**处理：** 
1. 如果配置了降级链，尝试下一个模型
2. 如果所有模型都失败，终止 run 并记录错误
3. 记录到 Langfuse 和 Ledger

---

**场景：** 向量数据库连接失败

```python
# 行为：降级到仅使用 MEMORY.md

WARNING: Vector DB connection failed, falling back to MEMORY.md only
```

**处理：**
1. recall 工具返回空结果（而不是错误）
2. remember 工具仍然写入 MEMORY.md（但不索引到向量 DB）
3. 记录降级事件到 Ledger

---

**场景：** 工具执行失败

```python
# 行为：将错误信息返回给 LLM

{
    "error": "Tool 'check_entry_opportunity' execution failed: 
              ConnectionError: Database connection timeout"
}
```

**处理：**
1. 捕获工具执行异常
2. 将错误信息格式化为 dict
3. 返回给 LLM 作为 tool result
4. LLM 可以基于错误信息做出后续决策（如重试、跳过、调用其他工具）

---

**场景：** Function calling 次数超限

```python
# 行为：终止 run，记录警告

WARNING: Agent run terminated: function call limit (50) exceeded
```

**处理：**
1. 终止 LLM 循环
2. 记录警告到日志和 Ledger
3. 返回 run 结果，状态为 "terminated"

---

**场景：** Agent Run 超时

```python
# 行为：终止 run，记录超时错误

TimeoutError: Agent run exceeded timeout (300s)
```

**处理：**
1. 通过 asyncio.wait_for 检测超时
2. 取消所有未完成的异步任务
3. 记录超时错误到 Ledger
4. 返回 run 结果，状态为 "timeout"

---

### 3. 资源限制错误

**场景：** 短期记忆超过 token 限制

```python
# 行为：自动压缩

INFO: Short-term memory exceeded 2000 tokens, compressing...
```

**处理：**
1. 保留最近的 N 条记录
2. 压缩旧记录（提取关键信息）
3. 确保压缩后在限制内

---

**场景：** MEMORY.md 文件大小超限

```python
# 行为：自动归档

INFO: MEMORY.md size (10.5MB) exceeded limit (10MB), archiving old memories...
```

**处理：**
1. 将 3 个月前的记忆移至归档表
2. 从 MEMORY.md 删除归档的记忆
3. 更新向量索引（仅包含活跃记忆）

---

### 4. 配置错误

**场景：** 无效的配置项

```python
# 行为：启动时拒绝配置

ValueError: Invalid configuration: 
  llm_timeout must be positive, got -10
```

**处理：**
1. 在 setup() 时验证所有配置项
2. 如果验证失败，抛出 ValueError
3. 阻止 Agent Runtime 初始化

---

## 测试策略

### 1. 单元测试

**覆盖范围：**
- IdentityLoader: 文件加载、解析、热重载
- MemorySystem: 短期记忆构建、长期记忆读写、向量搜索
- KnowledgeInjector: Skills 加载、选择、token 限制
- HeartbeatChecker: 事件检查逻辑
- AgentRuntime: 决策循环、工具执行、错误处理

**Mock 对象：**
- LLM 客户端（mock litellm 响应）
- 向量数据库（mock 搜索结果）
- Hatchet 客户端（mock 任务调度）
- Langfuse 客户端（mock trace 创建）
- Capability Registry（mock 能力列表）
- Governance Layer（mock 过滤逻辑）

**测试框架：**
- pytest + pytest-asyncio
- pytest-mock（mock 对象）
- pytest-cov（覆盖率 > 80%）

---

### 2. 集成测试

**测试场景：**
- Agent Runtime 与真实 Hatchet 的集成
- Agent Runtime 与真实 litellm 的集成（使用测试 API key）
- Agent Runtime 与真实向量数据库的集成（pgvector 测试实例）
- Agent Runtime 与真实 Langfuse 的集成（测试项目）

**测试环境：**
- Docker Compose（Hatchet + PostgreSQL + pgvector）
- 测试数据库（隔离的 schema）
- 清理策略（每个测试后清理数据）

---

### 3. 端到端测试

**测试场景：**
- 完整的 Agent Run 流程（从触发到完成）
- Heartbeat 机制（无事件跳过 LLM，有事件触发完整 run）
- 身份热重载（修改文件后 reload，验证新内容生效）
- 记忆系统（remember → recall round-trip）
- Skills 注入（验证 Skills 内容在 system prompt 中）
- 错误恢复（LLM 失败降级、向量 DB 失败降级）

**验证点：**
- Agent Run 成功完成
- 所有工具调用被记录到 Ledger
- Langfuse trace 包含完整的 span
- 记忆被正确持久化
- 错误被正确处理和记录

---

### 4. 性能测试

**测试指标：**
- Agent Run 启动延迟（P50/P95/P99）
- LLM 调用延迟（取决于模型）
- 向量搜索延迟（P50/P95/P99）
- 并发 Agent Run 吞吐量
- 内存使用情况

**测试工具：**
- locust（负载测试）
- pytest-benchmark（性能基准）

---

### 5. 基于属性的测试（Property-Based Testing）

**测试库：** Hypothesis（Python）

**测试配置：**
- 每个属性测试最少 100 次迭代
- 每个测试标记为 `@pytest.mark.property`
- 每个测试包含注释：`# Feature: agent-runtime, Property N: <property_text>`

**测试覆盖：**
- 所有 23 个正确性属性都应该有对应的基于属性的测试
- 使用 Hypothesis 的 strategies 生成随机输入
- 验证属性在所有生成的输入上都成立

**示例：**

```python
from hypothesis import given, strategies as st
import pytest

@pytest.mark.property
@given(
    soul_content=st.text(min_size=10, max_size=10000),
    identity_content=st.text(min_size=10, max_size=10000),
)
def test_identity_loading_integrity(soul_content, identity_content, tmp_path):
    """
    Feature: agent-runtime, Property 1: 身份文件加载完整性
    
    For any valid SOUL.md and IDENTITY.md, initialization should succeed
    and content should be available in system prompt.
    """
    # Setup
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()
    (app_dir / "SOUL.md").write_text(soul_content)
    (app_dir / "IDENTITY.md").write_text(identity_content)
    
    # Execute
    loader = IdentityLoader(str(app_dir))
    await loader.load()
    identity = loader.get_identity()
    
    # Verify
    assert identity["soul"] == soul_content
    assert len(identity["capabilities_summary"]) > 0
```


## 依赖关系

### 外部依赖

- **litellm** (litellm): LLM 统一调用
- **langfuse** (langfuse): LLM 调用追踪
- **hatchet-sdk** (hatchet-sdk): 持久执行和任务调度
- **PyYAML** (pyyaml): SKILL.md frontmatter 解析
- **asyncio** (标准库): 异步执行和超时控制
- **pathlib** (标准库): 文件路径处理
- **dataclasses** (标准库): 数据类定义

### 内部依赖

- **owlclaw.integrations.hatchet**: Hatchet 客户端封装
- **owlclaw.integrations.llm**: litellm 客户端封装
- **owlclaw.integrations.langfuse**: Langfuse 客户端封装
- **owlclaw.agent.tools**: Agent 内建工具（Built-in Tools）
- **owlclaw.capabilities.registry**: 业务能力注册表（Capability Registry）
- **owlclaw.capabilities.skills**: Skills 加载和管理（待实现，可能合并到本模块）
- **owlclaw.governance.visibility**: 工具可见性过滤（Governance Layer）
- **owlclaw.governance.ledger**: 执行记录（Ledger）
- **owlclaw.db**: 数据库访问（PostgreSQL）
- **向量数据库客户端**: pgvector、Qdrant 等（业务应用配置）

### 依赖注入

AgentRuntime 通过构造函数接受所有依赖，便于测试和替换：

```python
# 生产环境
runtime = AgentRuntime(
    agent_id="mionyee-trading",
    app_dir="/path/to/mionyee",
    hatchet_client=hatchet_client,
    llm_client=llm_client,
    langfuse_client=langfuse_client,
    capability_registry=registry,
    governance_layer=governance,
    built_in_tools=tools,
    vector_db=vector_db,
    config=config,
)

# 测试环境
runtime = AgentRuntime(
    agent_id="test-agent",
    app_dir="/tmp/test_app",
    hatchet_client=mock_hatchet,
    llm_client=mock_llm,
    langfuse_client=mock_langfuse,
    capability_registry=mock_registry,
    governance_layer=mock_governance,
    built_in_tools=mock_tools,
    vector_db=mock_vector_db,
    config=test_config,
)
```

---

## 性能考虑

### 1. Agent Run 启动延迟

**目标：** P95 < 1 秒（不包括 LLM 调用）

**优化措施：**
- Skills metadata 在启动时加载并缓存
- Skills 完整内容按需加载并缓存
- 短期记忆构建使用高效的字符串拼接
- 向量搜索使用索引优化（HNSW 或 IVF）

---

### 2. LLM 调用延迟

**目标：** 取决于模型（GPT-4: ~2-5 秒，Claude: ~1-3 秒）

**优化措施：**
- 使用 litellm 的流式响应（streaming）
- 压缩 system prompt（移除冗余信息）
- 使用更快的模型作为降级选项
- 缓存 LLM 响应（相同 prompt 返回缓存结果）

---

### 3. 向量搜索延迟

**目标：** P95 < 200ms

**优化措施：**
- 使用高性能向量数据库（pgvector with HNSW index）
- 限制搜索结果数量（最多 20 条）
- 查询缓存（相同 query 在短时间内返回缓存结果）
- 异步搜索（不阻塞其他操作）

---

### 4. 内存使用

**目标：** 单次 run < 512MB

**优化措施：**
- 限制短期记忆大小（最多 20 条记录）
- 限制 Skills 注入 token 数（最多 4000 tokens）
- 限制 system prompt 总大小（最多 8000 tokens）
- 及时清理已完成 run 的内存

---

### 5. 并发控制

**问题：** 多个 Agent Run 并发执行可能导致资源竞争。

**解决方案：**
- 同一 Agent 的 run 串行执行（通过 Hatchet 并发控制）
- 不同 Agent 的 run 并行执行
- 向量数据库支持并发读写
- Ledger 支持并发写入

---

## 安全考虑

### 1. 输入 Sanitization

**风险：** 恶意内容可能导致 prompt injection。

**缓解：**
- SOUL.md、IDENTITY.md、SKILL.md 内容进行 HTML/SQL 转义
- 移除或转义特殊字符（如 `<script>`、`${}`）
- 限制文件大小（SOUL.md < 10KB，IDENTITY.md < 10KB，SKILL.md < 50KB）

---

### 2. 文件路径限制

**风险：** Agent 可能访问任意文件。

**缓解：**
- 所有文件路径必须相对于 app_dir
- 禁止使用 `..` 访问父目录
- 验证文件路径在 app_dir 内

---

### 3. 资源限制

**风险：** Agent 可能耗尽系统资源。

**缓解：**
- 限制单次 run 的最大内存使用（512MB）
- 限制单次 run 的最大执行时间（5 分钟）
- 限制 function calling 次数（50 次）
- 限制 LLM 调用超时（60 秒）

---

### 4. 审计日志

**风险：** Agent 行为不可追溯。

**缓解：**
- 所有 Agent Run 记录到 Ledger
- 所有 LLM 调用记录到 Langfuse
- 所有工具调用记录到 Ledger
- 所有错误记录到日志和 Ledger

---

### 5. 权限控制

**风险：** Agent 可能访问其他 Agent 的数据。

**缓解：**
- 所有数据库查询包含 agent_id 过滤
- 向量数据库使用独立的 collection（per agent）
- MEMORY.md 文件路径包含 agent_id
- Ledger 记录包含 agent_id

---

## 未来扩展

### 1. 多 Agent 协作

**需求：** 支持多个 Agent 之间的协作和通信。

**实现：**
- Agent 之间通过消息队列通信
- 支持 Agent 调用其他 Agent 的能力
- 支持 Agent 之间的记忆共享（可选）

---

### 2. Agent 学习和进化

**需求：** Agent 能够从经验中学习，优化决策策略。

**实现：**
- 记录 Agent 决策和结果到数据库
- 定期分析决策质量（成功率、成本、延迟）
- 基于分析结果调整 system prompt 或工具可见性

---

### 3. 可视化 Agent 决策过程

**需求：** 提供 UI 可视化 Agent 的决策过程。

**实现：**
- 基于 Langfuse trace 构建决策树可视化
- 显示每次 function calling 的输入输出
- 显示 Agent 的记忆和知识上下文

---

### 4. Agent 模板和预设

**需求：** 提供常见场景的 Agent 模板。

**实现：**
- 预设 SOUL.md 和 IDENTITY.md 模板
- 预设 Skills 库（如交易、客服、数据分析）
- 支持从模板快速创建新 Agent

---

### 5. Agent 性能优化

**需求：** 自动优化 Agent 的性能（延迟、成本）。

**实现：**
- 自动选择最优的 LLM 模型（基于任务类型）
- 自动压缩 system prompt（移除冗余信息）
- 自动缓存 LLM 响应（相同 prompt）
- 自动调整 Skills 注入策略（基于相关性）

---

## 参考

- OwlClaw 架构文档 `docs/ARCHITECTURE_ANALYSIS.md` §5（Agent 运行时设计）
- Agent Skills 规范（agentskills.io）
- OpenClaw 的 Agent 实现（SOUL.md、MEMORY.md、Skills）
- agent-tools spec（内建工具接口）
- litellm 文档（LLM 统一调用）
- Hatchet 文档（持久执行）
- Langfuse 文档（LLM 追踪）
- Hypothesis 文档（Property-Based Testing）
