# Configuration 系统设计文档

## 文档联动

- requirements: `.kiro/specs/configuration/requirements.md`
- design: `.kiro/specs/configuration/design.md`
- tasks: `.kiro/specs/configuration/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

OwlClaw 统一配置系统采用 **YAML + Pydantic BaseSettings + 环境变量** 三层合并架构，为所有模块提供类型安全、可验证、可热更新的配置管理。

## 技术栈统一与架构对齐

1. 配置系统核心实现统一 Python（Pydantic + YAML），不引入多语言配置引擎分叉。
2. 配置读取入口统一经 `ConfigManager`，禁止模块私有配置旁路。
3. 对外契约使用纯数据结构（YAML / env var / dict），不暴露 Python 特有对象到协议层。
4. 热更新只允许白名单字段，连接类配置保持冷更新（重启生效）。

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 配置加载优先级（defaults < yaml < env < runtime）必须稳定且可测试，不允许模块私有配置旁路。
2. 热更新仅限声明为可热更新字段，涉及安全/连接字段时必须触发明确重载策略。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Pipeline                     │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Defaults  │→ │  YAML    │→ │ Env Vars │→ │ app.config  │ │
│  │ (Pydantic)│  │  File    │  │ OWLCLAW_ │  │ ure() code  │ │
│  │ 优先级 0   │  │ 优先级 1  │  │ 优先级 2  │  │ 优先级 3     │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
│         │            │              │              │          │
│         └────────────┴──────────────┴──────────────┘          │
│                              │                                │
│                    ┌─────────▼──────────┐                    │
│                    │  OwlClawConfig     │                    │
│                    │  (Pydantic Root)   │                    │
│                    └─────────┬──────────┘                    │
│                              │                                │
│          ┌───────┬───────┬───┴───┬──────────┬──────────┐    │
│          │       │       │       │          │          │    │
│      AgentCfg GovCfg TrigCfg IntegCfg  SecCfg  MemoryCfg  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              ConfigManager (Singleton)                  │  │
│  │  - load()           → 首次加载                          │  │
│  │  - reload()         → 热更新（部分字段）                 │  │
│  │  - get()            → 获取当前配置                       │  │
│  │  - on_change(cb)    → 注册变更回调                       │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 配置模型层次

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class AgentConfig(BaseModel):
    soul: str = "docs/SOUL.md"
    identity: str = "docs/IDENTITY.md"
    heartbeat_interval_minutes: int = Field(30, ge=1, le=1440)
    max_iterations: int = Field(10, ge=1, le=100)
    stm_max_tokens: int = Field(2000, ge=500, le=8000)

class GovernanceConfig(BaseModel):
    monthly_budget: float = Field(500.0, ge=0)
    budget_alert_thresholds: list[float] = [0.5, 0.8, 1.0]
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()

class TriggersConfig(BaseModel):
    cron: CronTriggersConfig = CronTriggersConfig()
    webhook: WebhookTriggersConfig = WebhookTriggersConfig()
    db_change: DbChangeTriggersConfig = DbChangeTriggersConfig()
    api: ApiTriggersConfig = ApiTriggersConfig()
    signal: SignalTriggersConfig = SignalTriggersConfig()

class IntegrationsConfig(BaseModel):
    llm: LLMConfig = LLMConfig()
    hatchet: HatchetConfig = HatchetConfig()
    langfuse: LangfuseConfig = LangfuseConfig()

class SecurityConfig(BaseModel):
    sanitizer: SanitizerConfig = SanitizerConfig()
    risk_gate: RiskGateConfig = RiskGateConfig()
    data_masker: DataMaskerConfig = DataMaskerConfig()

class MemoryConfig(BaseModel):
    vector_backend: str = "pgvector"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    max_entries: int = 10000
    retention_days: int = 365

class OwlClawConfig(BaseSettings):
    """根配置，支持 Pydantic BaseSettings 的 env var 自动解析"""
    agent: AgentConfig = AgentConfig()
    governance: GovernanceConfig = GovernanceConfig()
    triggers: TriggersConfig = TriggersConfig()
    integrations: IntegrationsConfig = IntegrationsConfig()
    security: SecurityConfig = SecurityConfig()
    memory: MemoryConfig = MemoryConfig()

    model_config = SettingsConfigDict(
        env_prefix="OWLCLAW_",
        env_nested_delimiter="__",
    )
```

### 2. ConfigManager（单例管理器）

```python
class ConfigManager:
    _instance: ClassVar[Optional["ConfigManager"]] = None
    _config: OwlClawConfig
    _listeners: list[Callable[[OwlClawConfig, OwlClawConfig], None]]
    _hot_reloadable: ClassVar[set[str]] = {
        "governance", "security", "triggers",
    }
    _cold_only: ClassVar[set[str]] = {
        "integrations.hatchet", "integrations.langfuse",
        "memory.vector_backend", "memory.embedding_dimensions",
    }

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
        overrides: dict | None = None,
    ) -> "ConfigManager":
        """首次加载配置"""
        # 1. 从 Pydantic defaults 创建基础配置
        # 2. 加载 YAML 文件合并
        # 3. Pydantic BaseSettings 自动合并 env vars
        # 4. 应用 overrides（app.configure()）
        # 5. 验证并冻结
        ...

    def reload(self) -> ReloadResult:
        """热更新可热更新的配置段"""
        old = self._config
        new = self._load_fresh()
        changes = self._diff(old, new)
        hot_changes = {k: v for k, v in changes.items()
                       if self._is_hot_reloadable(k)}
        cold_skipped = {k: v for k, v in changes.items()
                        if not self._is_hot_reloadable(k)}
        self._config = self._apply_hot(old, hot_changes)
        self._notify_listeners(old, self._config)
        return ReloadResult(applied=hot_changes, skipped=cold_skipped)

    def get(self) -> OwlClawConfig:
        return self._config

    def on_change(self, callback: Callable) -> None:
        self._listeners.append(callback)
```

### 3. YAML 解析与错误处理

```python
class YAMLConfigLoader:
    def load(self, path: Path) -> dict:
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
        except yaml.YAMLError as e:
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                raise ConfigError(
                    f"YAML 解析错误 {path}:{mark.line+1}:{mark.column+1}: {e.problem}"
                )
            raise ConfigError(f"YAML 解析错误 {path}: {e}")
```

### 4. 环境变量映射规则

| 配置路径 | 环境变量 |
|----------|----------|
| `agent.heartbeat_interval_minutes` | `OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES` |
| `integrations.llm.model` | `OWLCLAW_INTEGRATIONS__LLM__MODEL` |
| `governance.monthly_budget` | `OWLCLAW_GOVERNANCE__MONTHLY_BUDGET` |
| `security.risk_gate.enabled` | `OWLCLAW_SECURITY__RISK_GATE__ENABLED` |

分隔符使用双下划线 `__`（Pydantic BaseSettings 标准行为）。

### 5. 热更新机制

**可热更新**：
- `governance.*` — 预算、限流、熔断参数
- `security.*` — sanitizer 规则、risk gate 参数、脱敏规则
- `triggers.*.max_concurrent` / `timeout` 等运行参数

**不可热更新（需重启）**：
- `integrations.hatchet.*` — 连接参数
- `integrations.langfuse.*` — 连接参数
- `memory.vector_backend` — 向量后端类型
- `memory.embedding_dimensions` — 向量维度
- `agent.soul` / `agent.identity` — 身份文件路径

热更新流程：
```
owlclaw reload
  → CLI 发送 SIGHUP (Unix) 或 HTTP POST /admin/reload (Windows)
  → ConfigManager.reload()
  → diff(old, new)
  → 应用 hot_reloadable 变更
  → 通知 listeners（governance、security 模块重新加载规则）
  → 返回 applied + skipped 报告
```

### 6. app.configure() 集成

```python
class OwlClaw:
    def configure(self, **kwargs):
        """代码级配置覆盖（优先级最高）"""
        # 扁平化 kwargs → 嵌套 dict
        # 例: heartbeat_interval_minutes=30 → {"agent": {"heartbeat_interval_minutes": 30}}
        # 例: soul="docs/SOUL.md" → {"agent": {"soul": "docs/SOUL.md"}}
        overrides = self._flatten_to_nested(kwargs)
        ConfigManager.load(overrides=overrides)
```

## 数据流

```
应用启动
  │
  ├─ 1. 查找 config 文件：
  │     OWLCLAW_CONFIG env → --config CLI → ./owlclaw.yaml → 默认值
  │
  ├─ 2. ConfigManager.load(config_path)
  │     │
  │     ├─ Pydantic defaults
  │     ├─ + YAML merge
  │     ├─ + env vars merge (OWLCLAW_ prefix)
  │     ├─ + app.configure() overrides
  │     └─ → OwlClawConfig（validated, frozen）
  │
  ├─ 3. 各模块从 ConfigManager.get() 读取配置
  │     │
  │     ├─ AgentRuntime  → config.agent
  │     ├─ Governance    → config.governance
  │     ├─ MemoryService → config.memory
  │     └─ ...
  │
  └─ 运行时 owlclaw reload
        │
        └─ ConfigManager.reload() → 仅更新 hot_reloadable 字段
```

## 错误处理

| 场景 | 行为 |
|------|------|
| YAML 文件不存在 | 使用默认值 + 日志 WARNING |
| YAML 语法错误 | 抛出 ConfigError（含行号列号） |
| Pydantic 验证失败 | 抛出 ValidationError（含字段路径和原因） |
| 环境变量类型错误 | 抛出 ValidationError |
| reload 时新配置无效 | 回滚到旧配置 + 日志 ERROR |

## 测试策略

| 层级 | 覆盖 | 工具 |
|------|------|------|
| 单元测试 | Pydantic 模型默认值、验证、边界条件 | pytest |
| 单元测试 | YAML 解析、错误消息 | pytest + 临时文件 |
| 单元测试 | 环境变量覆盖优先级 | pytest + monkeypatch |
| 单元测试 | 热更新 diff + 应用 + 回滚 | pytest |
| 集成测试 | ConfigManager 完整加载流程 | pytest |
| 集成测试 | app.configure() 覆盖链 | pytest |
