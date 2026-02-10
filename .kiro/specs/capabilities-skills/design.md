# 设计文档

## 简介

本文档描述了 OwlClaw 能力注册和 Skills 挂载系统的技术设计。该系统由三个核心组件组成：

1. **Skills_Loader** — 从应用目录发现和加载 SKILL.md 文件
2. **Capability_Registry** — 管理 handlers 和 states 的注册与调用
3. **Knowledge_Injector** — 将 Skills 知识注入到 Agent prompts 中

该设计遵循 Agent Skills 开放规范（Anthropic，2025年12月），同时支持 OwlClaw 特定的扩展字段。

## 架构概览

```
业务应用
├── capabilities/
│   ├── entry-monitor/
│   │   ├── SKILL.md              # Agent Skills 规范
│   │   ├── references/
│   │   │   └── trading-rules.md
│   │   └── scripts/
│   │       └── check_signals.py
│   └── morning-decision/
│       └── SKILL.md
└── app.py

app.py:
  from owlclaw import OwlClaw
  
  app = OwlClaw("mionyee-trading")
  app.mount_skills("./capabilities/")  # Skills_Loader 扫描
  
  @app.handler("entry-monitor")       # Capability_Registry 注册
  async def check_entry(session):
      ...
  
  @app.state("market_state")          # Capability_Registry 注册
  async def get_market_state():
      ...
```

### 数据流

```
启动时:
  mount_skills() → Skills_Loader.scan()
                → 解析 frontmatter
                → 存储元数据（不加载完整内容）
                → 返回 Skill 对象列表

  @handler() → Capability_Registry.register_handler()
            → 验证 Skill 存在
            → 存储 handler 函数引用

Agent Run 时:
  构建 prompt → Knowledge_Injector.get_skills_knowledge()
              → Skills_Loader.load_full_content()
              → 格式化为 Markdown
              → 注入 system prompt

  function call → Capability_Registry.invoke_handler()
                → 查找 handler
                → 执行并返回结果
```



## 组件设计

### 1. Skills_Loader

**职责：** 从文件系统发现、解析和加载 SKILL.md 文件。

#### 1.1 类定义

```python
from pathlib import Path
import logging
import yaml

logger = logging.getLogger(__name__)


class Skill:
    """Represents a loaded Skill with metadata and optional full content."""
    
    def __init__(
        self,
        name: str,
        description: str,
        file_path: Path,
        metadata: dict,
        owlclaw_config: dict | None = None,
        full_content: str | None = None,
    ):
        self.name = name
        self.description = description
        self.file_path = file_path
        self.metadata = metadata  # Agent Skills 标准字段
        self.owlclaw_config = owlclaw_config or {}
        self._full_content = full_content
        self._is_loaded = full_content is not None
    
    @property
    def task_type(self) -> str | None:
        return self.owlclaw_config.get("task_type")
    
    @property
    def constraints(self) -> dict:
        return self.owlclaw_config.get("constraints", {})
    
    @property
    def trigger(self) -> str | None:
        return self.owlclaw_config.get("trigger")
    
    def load_full_content(self) -> str:
        """Load full instruction text from SKILL.md (lazy loading)."""
        if not self._is_loaded:
            self._full_content = self.file_path.read_text(encoding="utf-8")
            # Extract content after frontmatter
            parts = self._full_content.split("---", 2)
            if len(parts) >= 3:
                self._full_content = parts[2].strip()
            self._is_loaded = True
        return self._full_content
    
    @property
    def references_dir(self) -> Path | None:
        """Path to references/ directory if it exists."""
        ref_dir = self.file_path.parent / "references"
        return ref_dir if ref_dir.exists() else None
    
    @property
    def scripts_dir(self) -> Path | None:
        """Path to scripts/ directory if it exists."""
        scripts_dir = self.file_path.parent / "scripts"
        return scripts_dir if scripts_dir.exists() else None
    
    def to_dict(self) -> dict:
        """Serialize metadata to dict (excludes full content)."""
        return {
            "name": self.name,
            "description": self.description,
            "file_path": str(self.file_path),
            "metadata": self.metadata,
            "task_type": self.task_type,
            "constraints": self.constraints,
            "trigger": self.trigger,
        }


class SkillsLoader:
    """Discovers and loads SKILL.md files from application directories."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.skills: dict[str, Skill] = {}
    
    def scan(self) -> list[Skill]:
        """Recursively scan for SKILL.md files and load metadata."""
        skill_files = self.base_path.rglob("SKILL.md")
        
        for skill_file in skill_files:
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    self.skills[skill.name] = skill
            except Exception as e:
                logger.warning("Failed to parse %s: %s", skill_file, e)
        
        return list(self.skills.values())
    
    def _parse_skill_file(self, file_path: Path) -> Skill | None:
        """Parse SKILL.md file and extract frontmatter metadata."""
        content = file_path.read_text(encoding="utf-8")
        
        # Extract YAML frontmatter
        if not content.startswith("---"):
            logger.warning("Skill file %s missing frontmatter", file_path)
            return None
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.warning("Skill file %s invalid frontmatter format", file_path)
            return None
        
        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            logger.warning("Skill file %s YAML parse error: %s", file_path, e)
            return None
        
        # Validate required fields
        if "name" not in frontmatter or "description" not in frontmatter:
            logger.warning("Skill file %s missing required fields (name, description)", file_path)
            return None
        
        # Extract Agent Skills standard fields
        metadata = frontmatter.get("metadata", {})
        
        # Extract OwlClaw extension fields
        owlclaw_config = frontmatter.get("owlclaw", {})
        
        return Skill(
            name=frontmatter["name"],
            description=frontmatter["description"],
            file_path=file_path,
            metadata=metadata,
            owlclaw_config=owlclaw_config,
            full_content=None,  # Lazy loading
        )
    
    def get_skill(self, name: str) -> Skill | None:
        """Retrieve a Skill by name."""
        return self.skills.get(name)
    
    def list_skills(self) -> list[Skill]:
        """List all loaded Skills."""
        return list(self.skills.values())
```



### 2. Capability_Registry

**职责：** 管理 handlers 和 states 的注册、查找和调用。

#### 2.1 类定义

```python
from typing import Callable, Any
from collections.abc import Awaitable
import inspect
import logging

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for capability handlers and state providers."""
    
    def __init__(self, skills_loader: SkillsLoader):
        self.skills_loader = skills_loader
        self.handlers: dict[str, Callable] = {}
        self.states: dict[str, Callable] = {}
    
    def register_handler(self, skill_name: str, handler: Callable) -> None:
        """Register a handler function for a Skill."""
        # Validate Skill exists
        skill = self.skills_loader.get_skill(skill_name)
        if not skill:
            logger.warning("Registering handler for non-existent Skill '%s'", skill_name)
        
        # Check for duplicate registration
        if skill_name in self.handlers:
            raise ValueError(
                f"Handler for '{skill_name}' already registered. "
                f"Existing: {self.handlers[skill_name].__name__}, "
                f"New: {handler.__name__}"
            )
        
        self.handlers[skill_name] = handler
    
    def register_state(self, state_name: str, provider: Callable) -> None:
        """Register a state provider function."""
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
    
    async def invoke_handler(
        self, 
        skill_name: str, 
        **kwargs
    ) -> Any:
        """Invoke a registered handler by Skill name."""
        handler = self.handlers.get(skill_name)
        if not handler:
            raise ValueError(
                f"No handler registered for Skill '{skill_name}'"
            )
        
        try:
            if inspect.iscoroutinefunction(handler):
                return await handler(**kwargs)
            else:
                return handler(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Handler '{skill_name}' failed: {e}"
            ) from e
    
    async def get_state(self, state_name: str) -> dict:
        """Get state from a registered state provider."""
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
        """List all registered capabilities with metadata."""
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
        """Get metadata for a specific capability."""
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
        """Filter capabilities by task_type."""
        matching = []
        
        for skill_name in self.handlers.keys():
            skill = self.skills_loader.get_skill(skill_name)
            if skill and skill.task_type == task_type:
                matching.append(skill_name)
        
        return matching
```



### 3. Knowledge_Injector

**职责：** 将 Skills 知识格式化并注入到 Agent prompts 中。

#### 3.1 类定义

```python
class KnowledgeInjector:
    """Formats and injects Skills knowledge into Agent prompts."""
    
    def __init__(self, skills_loader: SkillsLoader):
        self.skills_loader = skills_loader
    
    def get_skills_knowledge(
        self, 
        skill_names: list[str],
        context_filter: Callable[[Skill], bool] | None = None
    ) -> str:
        """
        Retrieve and format Skills knowledge for specified Skills.
        
        Args:
            skill_names: List of Skill names to include
            context_filter: Optional filter function to exclude Skills
                           based on context (e.g., trading hours)
        
        Returns:
            Formatted Markdown string with Skills knowledge
        """
        knowledge_parts = []
        
        for skill_name in skill_names:
            skill = self.skills_loader.get_skill(skill_name)
            if not skill:
                continue
            
            # Apply context filter if provided
            if context_filter and not context_filter(skill):
                continue
            
            # Load full content (lazy loading)
            full_content = skill.load_full_content()
            
            # Format as Markdown section
            knowledge_parts.append(
                f"## Skill: {skill.name}\n\n"
                f"**Description:** {skill.description}\n\n"
                f"{full_content}\n"
            )
        
        if not knowledge_parts:
            return ""
        
        return (
            "# Available Skills\n\n"
            "The following Skills describe your capabilities and "
            "when to use them:\n\n"
            + "\n---\n\n".join(knowledge_parts)
        )
    
    def get_all_skills_summary(self) -> str:
        """Get a summary of all Skills (metadata only, no full content)."""
        skills = self.skills_loader.list_skills()
        
        if not skills:
            return "No Skills available."
        
        summary_parts = [
            "# Available Skills Summary\n\n"
            "You have access to the following capabilities:\n"
        ]
        
        for skill in skills:
            summary_parts.append(
                f"- **{skill.name}**: {skill.description}"
            )
        
        return "\n".join(summary_parts)
```



### 4. OwlClaw 应用集成

**职责：** 提供用户友好的 API 来挂载 Skills 和注册 handlers。

#### 4.1 装饰器实现

```python
import logging
logger = logging.getLogger(__name__)


class OwlClaw:
    """Main OwlClaw application class."""
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.skills_loader: SkillsLoader | None = None
        self.registry: CapabilityRegistry | None = None
        self.knowledge_injector: KnowledgeInjector | None = None
    
    def mount_skills(self, capabilities_dir: str) -> None:
        """Mount Skills from application capabilities directory."""
        self.skills_loader = SkillsLoader(Path(capabilities_dir))
        skills = self.skills_loader.scan()
        
        self.registry = CapabilityRegistry(self.skills_loader)
        self.knowledge_injector = KnowledgeInjector(self.skills_loader)
        
        logger.info("Loaded %d Skills from %s", len(skills), capabilities_dir)
    
    def handler(self, skill_name: str):
        """Decorator to register a capability handler."""
        def decorator(func: Callable) -> Callable:
            if not self.registry:
                raise RuntimeError(
                    "Must call mount_skills() before registering handlers"
                )
            
            self.registry.register_handler(skill_name, func)
            return func
        
        return decorator
    
    def state(self, state_name: str):
        """Decorator to register a state provider."""
        def decorator(func: Callable) -> Callable:
            if not self.registry:
                raise RuntimeError(
                    "Must call mount_skills() before registering states"
                )
            
            self.registry.register_state(state_name, func)
            return func
        
        return decorator
```

#### 4.2 使用示例

```python
from owlclaw import OwlClaw

app = OwlClaw("mionyee-trading")

# Mount Skills from capabilities directory
app.mount_skills("./capabilities/")

# Register handlers
@app.handler("entry-monitor")
async def check_entry_opportunity(session) -> dict:
    """Check for entry opportunities in monitored positions."""
    monitor_service = get_entry_monitor_service()
    return await monitor_service.check_entry_opportunities(
        session=session, 
        user_id=DEFAULT_USER_ID
    )

@app.handler("morning-decision")
async def morning_decision(session) -> dict:
    """Make pre-market trading decisions."""
    decision_service = get_morning_decision_service()
    return await decision_service.make_morning_decision(
        session=session,
        user_id=DEFAULT_USER_ID
    )

# Register state providers
@app.state("market_state")
async def get_market_state() -> dict:
    """Get current market state."""
    return {
        "is_trading_time": is_trading_time(),
        "phase": get_current_market_phase(),
        "volatility": get_current_volatility(),
    }

@app.state("position_summary")
async def get_position_summary() -> dict:
    """Get summary of current positions."""
    return {
        "total_positions": get_position_count(),
        "total_value": get_total_position_value(),
        "top_holdings": get_top_holdings(limit=5),
    }
```



## 数据模型

### SKILL.md 文件格式

```yaml
---
# ── Agent Skills 标准字段 ──
name: entry-monitor
description: 检查持仓股票的入场机会，当价格到达入场区间时识别建仓时机

metadata:
  author: mionyee-team
  version: "1.0"
  tags: [trading, monitoring]

# ── OwlClaw 扩展字段 ──
owlclaw:
  task_type: trading_decision
  constraints:
    trading_hours_only: true
    cooldown_seconds: 300
    max_daily_calls: 50
  trigger: cron("*/60 * * * * *")
---

# 入场机会检查 — 使用指南

## 什么时候应该调用这个能力

- 交易时间内（09:30-15:00），当市场有波动时
- 大盘出现急跌后的反弹信号
- 个股到达你之前设定的目标价位

## 什么时候不应该调用

- 非交易时间
- 刚执行过（5分钟内），除非市场出现剧烈变化
- 当天已经建仓3次以上（风控限制）

## 调用后如何解读结果

- `opportunities` 为空 → 降低检查频率
- `opportunities` 非空 → 评估质量，决定是否调用 execute_entry

## 与其他能力的关系

- 发现机会后，通常接着调用 `execute_entry`
- 波动大时，先调用 `query_state("market_state")` 确认市场阶段
```

### Skill 对象结构

```python
{
    "name": "entry-monitor",
    "description": "检查持仓股票的入场机会...",
    "file_path": "/path/to/capabilities/entry-monitor/SKILL.md",
    "metadata": {
        "author": "mionyee-team",
        "version": "1.0",
        "tags": ["trading", "monitoring"]
    },
    "task_type": "trading_decision",
    "constraints": {
        "trading_hours_only": true,
        "cooldown_seconds": 300,
        "max_daily_calls": 50
    },
    "trigger": "cron(\"*/60 * * * * *\")"
}
```

### Capability 元数据结构

```python
{
    "name": "entry-monitor",
    "description": "检查持仓股票的入场机会...",
    "task_type": "trading_decision",
    "constraints": {
        "trading_hours_only": true,
        "cooldown_seconds": 300,
        "max_daily_calls": 50
    },
    "handler": "check_entry_opportunity"
}
```



## 错误处理

### 1. SKILL.md 解析错误

```python
# 场景：YAML frontmatter 格式错误
# 行为：记录警告，跳过该 Skill，继续扫描其他文件

Warning: Failed to parse /path/to/SKILL.md: 
  YAML parse error: mapping values are not allowed here
```

### 2. 缺少必需字段

```python
# 场景：SKILL.md 缺少 name 或 description
# 行为：记录警告，跳过该 Skill

Warning: /path/to/SKILL.md missing required fields (name, description)
```

### 3. Handler 注册到不存在的 Skill

```python
# 场景：@handler("non-existent-skill")
# 行为：记录警告，但允许注册（可能 Skill 稍后加载）

Warning: Registering handler for non-existent Skill 'non-existent-skill'
```

### 4. 重复 Handler 注册

```python
# 场景：同一 Skill 注册两次 handler
# 行为：抛出 ValueError

ValueError: Handler for 'entry-monitor' already registered. 
  Existing: check_entry_v1, New: check_entry_v2
```

### 5. Handler 调用失败

```python
# 场景：handler 执行时抛出异常
# 行为：包装异常并传播，附带上下文信息

RuntimeError: Handler 'entry-monitor' failed: 
  DatabaseConnectionError: Unable to connect to PostgreSQL
```

### 6. 状态提供者返回非 dict

```python
# 场景：@state 装饰的函数返回非 dict 类型
# 行为：实现中先抛出 TypeError，被 except 捕获后包装为 RuntimeError 传播（与 handler 失败一致）

RuntimeError: State provider 'market_state' failed: State provider 'market_state' must return dict, got <class 'str'>
```



## 性能考虑

### 1. 渐进式加载

**问题：** 如果在启动时加载所有 Skills 的完整内容，会消耗大量内存和启动时间。

**解决方案：** 
- 启动时仅解析 frontmatter（~100 tokens/skill）
- Agent run 时按需加载完整指令文本
- Run 结束后释放缓存的完整内容

**效果：**
- 100 个 Skills，每个 2KB 完整内容 = 200KB
- 渐进式加载：启动时仅 ~10KB（frontmatter）
- 运行时仅加载相关的 3-5 个 Skills = ~10KB

### 2. 文件系统缓存

**问题：** 每次 Agent run 都重新读取 SKILL.md 文件会导致 I/O 开销。

**解决方案：**
- Skill 对象缓存完整内容（`_full_content` 字段）
- 首次加载后，后续访问直接返回缓存
- 可选：文件监听器检测 SKILL.md 变更并重新加载

### 3. 元数据查询优化

**问题：** 治理层频繁查询 capability 元数据（constraints、task_type）。

**解决方案：**
- Capability_Registry 维护元数据索引
- `list_capabilities()` 返回预构建的元数据列表
- `filter_by_task_type()` 使用索引而非遍历



## 测试策略

### 1. 单元测试

#### Skills_Loader 测试

```python
def test_scan_discovers_skill_files():
    # Given: capabilities 目录包含 SKILL.md 文件
    # When: SkillsLoader.scan() 被调用
    # Then: 返回 Skill 对象列表
    
def test_parse_valid_frontmatter():
    # Given: 有效的 SKILL.md 文件
    # When: 解析 frontmatter
    # Then: 提取 name、description、metadata、owlclaw 字段
    
def test_parse_invalid_yaml():
    # Given: YAML 格式错误的 SKILL.md
    # When: 解析 frontmatter
    # Then: 记录警告并返回 None
    
def test_missing_required_fields():
    # Given: 缺少 name 字段的 SKILL.md
    # When: 解析 frontmatter
    # Then: 记录警告并返回 None
    
def test_lazy_loading():
    # Given: Skill 对象已创建（仅元数据）
    # When: 首次调用 load_full_content()
    # Then: 从文件读取完整内容
    # When: 再次调用 load_full_content()
    # Then: 返回缓存的内容（不重新读取文件）
```

#### Capability_Registry 测试

```python
def test_register_handler():
    # Given: 已加载的 Skill
    # When: 使用 @handler 装饰器注册函数
    # Then: handler 被添加到 registry
    
def test_register_duplicate_handler():
    # Given: 已注册的 handler
    # When: 为同一 Skill 注册第二个 handler
    # Then: 抛出 ValueError
    
def test_invoke_handler_success():
    # Given: 已注册的 handler
    # When: 调用 invoke_handler()
    # Then: handler 被执行并返回结果
    
def test_invoke_handler_not_found():
    # Given: 未注册的 Skill 名称
    # When: 调用 invoke_handler()
    # Then: 抛出 ValueError
    
def test_invoke_handler_failure():
    # Given: handler 执行时抛出异常
    # When: 调用 invoke_handler()
    # Then: 异常被包装为 RuntimeError 并传播
```

#### Knowledge_Injector 测试

```python
def test_get_skills_knowledge():
    # Given: 指定的 Skill 名称列表
    # When: 调用 get_skills_knowledge()
    # Then: 返回格式化的 Markdown 知识文档
    
def test_context_filter():
    # Given: 带 trading_hours_only 约束的 Skill
    # When: 使用非交易时间的 context_filter
    # Then: 该 Skill 被排除在知识文档外
    
def test_empty_skills_list():
    # Given: 空的 Skill 名称列表
    # When: 调用 get_skills_knowledge()
    # Then: 返回空字符串
```

### 2. 集成测试

```python
def test_end_to_end_skill_loading_and_invocation():
    # Given: 包含 SKILL.md 文件的 capabilities 目录
    # When: 
    #   1. mount_skills() 扫描目录
    #   2. @handler 注册 handler
    #   3. Agent run 调用 invoke_handler()
    # Then: handler 成功执行并返回结果
    
def test_knowledge_injection_in_agent_prompt():
    # Given: 已加载的 Skills
    # When: 构建 Agent prompt
    # Then: 相关 Skills 的知识被注入到 system prompt
```

### 3. 属性测试（Property-Based Testing）

```python
@given(skill_name=st.text(), description=st.text())
def test_skill_serialization_roundtrip(skill_name, description):
    # Property: Skill.to_dict() 的输出可以被 JSON 序列化和反序列化
    skill = Skill(name=skill_name, description=description, ...)
    serialized = json.dumps(skill.to_dict())
    deserialized = json.loads(serialized)
    assert deserialized["name"] == skill_name
    assert deserialized["description"] == description
```



## 依赖关系

### 外部依赖

- **PyYAML** (`pyyaml`): YAML frontmatter 解析
- **pathlib** (标准库): 文件系统操作
- **inspect** (标准库): 函数签名检查

### 内部依赖

- **owlclaw.agent.runtime**: Agent 运行时将使用 Knowledge_Injector 构建 prompts
- **owlclaw.governance.visibility**: 治理层将使用 Capability_Registry 查询元数据
- **owlclaw.triggers**: 触发器将使用 Capability_Registry 调用 handlers

## 未来扩展

### 1. Skills 热重载

**需求：** 开发时修改 SKILL.md 后无需重启应用。

**实现：**
- 使用 `watchdog` 库监听 capabilities 目录
- 文件变更时重新解析并更新 Skill 对象
- 清除已缓存的完整内容

### 2. Skills 版本管理

**需求：** 支持同一 Skill 的多个版本共存。

**实现：**
- frontmatter 增加 `version` 字段
- Skill 名称格式：`entry-monitor@1.0`
- Registry 支持按版本查询

### 3. Skills 依赖声明

**需求：** Skill 可以声明依赖其他 Skills。

**实现：**
- frontmatter 增加 `dependencies` 字段
- Knowledge_Injector 自动加载依赖的 Skills
- 循环依赖检测

### 4. Skills 参数验证

**需求：** 在 SKILL.md 中声明 handler 的参数 schema。

**实现：**
- frontmatter 增加 `parameters` 字段（JSON Schema）
- Registry 在调用 handler 前验证参数
- 验证失败时返回清晰的错误消息

## 安全考虑

### 1. 路径遍历攻击

**风险：** 恶意的 SKILL.md 文件路径可能导致读取系统文件。

**缓解：**
- SkillsLoader 仅扫描指定的 `base_path` 目录
- 使用 `Path.resolve()` 规范化路径
- 拒绝 `base_path` 外的文件

### 2. YAML 反序列化漏洞

**风险：** 恶意的 YAML 可能执行任意代码。

**缓解：**
- 使用 `yaml.safe_load()` 而非 `yaml.load()`
- 不允许自定义 YAML 标签

### 3. Handler 执行隔离

**风险：** 恶意 handler 可能访问不应访问的资源。

**缓解：**
- Handler 执行在业务应用的权限范围内（OwlClaw 不提供额外隔离）
- 治理层的约束过滤提供第一道防线
- 业务应用负责自己的安全边界

