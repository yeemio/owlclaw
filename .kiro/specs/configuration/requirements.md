# Requirements: 统一配置系统

> **目标**：为 OwlClaw 提供统一的配置管理，基于 owlclaw.yaml + Pydantic + 环境变量  
> **优先级**：P1  
> **预估工作量**：3-5 天

---

## 1. 背景与动机

### 1.1 当前问题

架构文档 §6.4 技术栈指定 `YAML + Pydantic` 作为配置方案。当前各模块各自管理配置（环境变量、硬编码默认值），缺少统一的配置加载、验证和访问机制。

### 1.2 设计目标

- 提供 `owlclaw.yaml` 作为统一配置文件
- 使用 Pydantic 模型做类型安全的配置验证
- 支持环境变量覆盖（`OWLCLAW_` 前缀）
- 支持 `owlclaw reload` 热更新部分配置（治理规则、安全策略）

---

## 2. 用户故事

### 2.1 作为业务开发者

**故事 1**：统一配置入口
```
作为业务开发者
我希望通过一个 owlclaw.yaml 文件配置所有 OwlClaw 行为
这样我可以集中管理 Agent、治理、触发器、集成等配置
```

**验收标准**：
- [ ] `owlclaw.yaml` 覆盖 agent、governance、triggers、integrations、security 配置
- [ ] 配置文件路径通过 `OWLCLAW_CONFIG` 环境变量或 `--config` CLI 参数指定
- [ ] 缺少配置文件时使用合理的默认值

**故事 2**：环境变量覆盖
```
作为运维人员
我希望通过环境变量覆盖配置文件中的值
这样我可以在不修改文件的情况下调整配置（如 CI/CD、Docker）
```

**验收标准**：
- [ ] 环境变量格式：`OWLCLAW_<SECTION>_<KEY>`（如 `OWLCLAW_AGENT_HEARTBEAT_INTERVAL=30`）
- [ ] 环境变量优先级高于配置文件
- [ ] 支持嵌套配置的环境变量映射

---

## 3. 功能需求

#### FR-1：配置模型

**需求**：使用 Pydantic BaseSettings 定义类型安全的配置模型。

**验收标准**：
- [ ] 顶层配置：OwlClawConfig（agent, governance, triggers, integrations, security）
- [ ] 每个子配置为独立的 Pydantic 模型
- [ ] 所有字段有合理默认值和类型验证

#### FR-2：配置加载

**需求**：从 YAML 文件和环境变量加载配置，支持优先级合并。

**验收标准**：
- [ ] 优先级：环境变量 > owlclaw.yaml > 默认值
- [ ] YAML 解析错误时提供清晰的错误信息和行号
- [ ] 配置单例模式，全局可访问

#### FR-3：热更新

**需求**：部分配置（治理规则、安全策略）支持运行时热更新。

**验收标准**：
- [ ] `owlclaw reload` CLI 命令重新加载配置
- [ ] 不可热更新的配置（数据库、Hatchet 连接）在 reload 时跳过并提示
- [ ] 配置变更事件通知已注册的监听者

#### FR-4：`app.configure()` API

**需求**：支持代码中通过 `app.configure()` 设置配置（优先级最高）。

**验收标准**：
- [ ] `app.configure(soul="docs/SOUL.md", heartbeat_interval_minutes=30)` 
- [ ] 代码配置优先级高于环境变量和文件

---

## 4. 配置文件结构

```yaml
# owlclaw.yaml
agent:
  soul: docs/SOUL.md
  identity: docs/IDENTITY.md
  heartbeat_interval_minutes: 30
  max_iterations: 10

governance:
  monthly_budget: 500.0
  budget_alert_thresholds: [0.5, 0.8, 1.0]
  circuit_breaker:
    failure_threshold: 0.5
    window_size: 10

triggers:
  cron:
    max_concurrent: 10
    default_timeout: 300

integrations:
  llm:
    model: gpt-4o
    fallback_models: [gpt-4o-mini]
    temperature: 0.7
  hatchet:
    server_url: ${HATCHET_CLIENT_TOKEN}
  langfuse:
    enabled: false

security:
  sanitizer:
    enabled: true
  risk_gate:
    enabled: true
    confirmation_timeout_seconds: 300
```

---

## 5. 依赖

- pydantic / pydantic-settings：配置模型和环境变量加载
- PyYAML：YAML 解析

---

## 6. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §6.4 技术栈
- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.2.4 能力注册 — app.configure()

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
