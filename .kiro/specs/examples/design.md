# Design: 示例应用

## 文档联动

- requirements: `.kiro/specs/examples/requirements.md`
- design: `.kiro/specs/examples/design.md`
- tasks: `.kiro/specs/examples/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：提供端到端示例，覆盖多行业业务场景，展示 OwlClaw 各子系统协作  
> **状态**：进行中（已完成核心目录与可运行样例）  
> **最后更新**：2026-02-25

---

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 示例项目可使用 mock 数据替代真实依赖，但不得伪造核心行为结果（需可复现实验流程）。
2. 示例中的集成调用必须遵守核心边界（Hatchet/LLM/Langfuse 仅通过 integrations 层接入）。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 1. 架构设计

### 1.1 整体架构

示例以仓库内 `examples/` 目录组织，包含可直接运行的脚本样例和能力目录样例。

```
examples/
├── cron/                           # Cron 触发器示例（focus/治理/重试）
├── langchain/                      # LangChain runnable 集成示例
├── binding-http/                   # Declarative Binding（active/shadow/shell）
├── binding-openapi-e2e/            # OpenAPI -> binding 端到端示例
├── capabilities/                   # 能力目录（entry-monitor/morning-decision）
├── owlhub_skills/                  # 行业 Skills（analytics/monitoring/workflow）
│
└── mionyee-trading/                # 完整示例：交易系统（3 个核心任务）
    ├── skills/
    │   ├── entry-monitor/
    │   │   └── SKILL.md
    │   ├── morning-decision/
    │   │   └── SKILL.md
    │   └── knowledge-feedback/
    │       └── SKILL.md
    ├── app.py
    └── README.md
```

### 1.2 设计原则

1. **独立可运行**：每个示例 `cd examples/<name> && python app.py` 即可运行
2. **无外部依赖**：使用 mock 数据和 `mock_mode=True`，不需要真实数据库/Hatchet/LLM
3. **渐进复杂度**：从通用脚本与目录示例到完整场景（mionyee-trading）
4. **多行业覆盖**：至少覆盖电商、SaaS、金融 3 个行业
5. **展示核心特性**：每个示例突出 OwlClaw 的一个核心特性

### 1.3 核心特性覆盖矩阵

| 示例 | Skills | @handler | @cron | Webhook | Fallback | Governance | LangChain |
|------|--------|----------|-------|---------|----------|------------|-----------|
| cron | ✅ | ✅ | ✅ | | ✅ | ✅ | |
| binding-http | ✅ | ✅ | | ✅ | ✅ | ✅ | |
| langchain | ✅ | ✅ | ✅ | | ✅ | | ✅ |
| owlhub_skills | ✅ | | | | | | |
| mionyee-trading | ✅ | ✅ | ✅ | | ✅ | ✅ | |

---

## 2. 实现细节

### 2.1 示例 1：cron（最小示例）

**目标**：5 分钟上手，展示 Cron 替代的核心价值。

```python
# app.py
from owlclaw import OwlClaw

app = OwlClaw("cleanup-agent")

@app.cron(
    "0 2 * * *",
    event_name="nightly_cleanup",
    focus="maintenance",
)
async def cleanup_fallback() -> dict:
    return {"status": "fallback_ok", "task": "cleanup"}
```

### 2.2 示例 2：binding-http（API/Binding 场景）

**目标**：展示治理约束（成本控制、频率限制）和业务 Skills。

展示 active/shadow/fallback 三种执行路径，体现治理与观测约束。

### 2.3 示例 3：langchain（LangChain 集成）

**目标**：展示编排框架标准接入（架构决策 8）。

LangChain runnable 注册为 capability，OwlClaw Agent 自主决定何时调用。

```python
# LangChain chain 注册为 OwlClaw capability
@app.handler("knowledge-query", knowledge="skills/knowledge-query/SKILL.md")
async def query_kb(question: str) -> str:
    return await rag_chain.ainvoke(question)
```

### 2.4 示例 4：mionyee-trading（完整场景）

**目标**：展示 OwlClaw 的完整能力，3 个核心任务端到端验证。

对应架构文档 §6.1 MVP 目标。

---

## 3. 数据流

### 3.1 通用示例运行流程

```
python app.py
    │
    ├── OwlClaw 初始化（加载 Skills、注册 handlers、配置触发器）
    │
    ├── mock_mode=True → 使用 mock LLM 和 mock Hatchet
    │
    ├── 触发器触发（Cron tick / Webhook 请求 / 手动触发）
    │   │
    │   ▼
    │   Agent Run:
    │   ├── 加载相关 Skills（按 focus 过滤）
    │   ├── 构建 system prompt（SOUL + Skills 知识）
    │   ├── LLM function calling（mock 模式返回预设决策）
    │   ├── 执行 capability handler
    │   ├── 治理层记录（Ledger）
    │   └── 输出结果
    │
    └── 日志输出展示 Agent 决策过程
```

---

## 4. 错误处理

### 4.1 Mock 模式降级

**场景**：用户尝试在没有 Hatchet/LLM 的环境运行

**处理**：`mock_mode=True` 时自动使用内存调度器和 mock LLM 响应，无需任何外部服务。

### 4.2 依赖缺失

**场景**：langchain-rag-agent 示例需要 langchain 但未安装

**处理**：`ImportError` 时给出清晰提示：`pip install owlclaw[langchain]`

---

## 5. 配置

### 5.1 每个示例的 README 结构

```markdown
# [示例名称]

> [一句话描述]

## 快速开始

1. `cd examples/<name>`
2. `pip install owlclaw`
3. `python app.py`

## 展示的特性

- [特性 1]
- [特性 2]

## 代码结构

- `app.py` — 主入口
- `skills/` — SKILL.md 文档
- `handlers.py` — 业务函数

## 预期输出

[示例运行后的日志输出]
```

---

## 6. 测试策略

### 6.1 示例可运行测试

```python
# tests/test_examples.py
import subprocess

def test_simple_cron_example():
    result = subprocess.run(
        ["python", "examples/simple-cron/app.py", "--once"],
        capture_output=True, timeout=30
    )
    assert result.returncode == 0
```

### 6.2 CI 集成

每个示例在 CI 中作为独立测试运行，确保不会因代码变更而失效。

---

## 7. 迁移计划

### 7.1 Phase 1：核心示例目录（完成）
- [x] cron / langchain / binding-http / owlhub_skills 基础示例

### 7.2 Phase 2：完整业务示例（进行中）
- [x] mionyee-trading 示例目录与三任务技能文档
- [x] mionyee-trading 可运行性自动化测试

### 7.3 Phase 3：CI 与文档收口（待完成）
- [ ] 示例批量验证脚本持续纳入 CI 质量门禁

---

## 8. 风险与缓解

### 8.1 风险：Mock 模式与真实行为不一致

**影响**：用户在 mock 模式下运行正常，切换到真实环境后出问题

**缓解**：
- Mock 返回的数据结构与真实 LLM 一致
- README 明确说明 mock vs production 的差异
- 提供 docker-compose.yml 用于真实环境快速搭建

---

## 9. 契约与 Mock

### 9.1 Mock 策略

所有示例使用 `mock_mode=True`，包括：
- Mock LLM：返回预设的 function calling 决策
- Mock Hatchet：使用内存调度器
- Mock 数据：使用 Python dict 模拟数据库

---

## 10. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §2.7.3 SKILL.md 场景示例
- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §4.8 编排框架标准接入
- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §6.1 MVP 目标

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
