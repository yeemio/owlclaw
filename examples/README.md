# OwlClaw Examples

示例应用，展示如何用 OwlClaw 让成熟业务系统获得 AI 自主能力。

## 示例列表

| 示例 | 场景 | 复杂度 |
|------|------|--------|
| `mionyee-trading/` | 交易系统完整接入示例（3 core skills + identity docs） | 高 |
| `cron/` | Cron 触发器完整示例（focus/治理/重试） | 中 |
| `langchain/` | LangChain runnable 集成（注册/重试/流式/追踪） | 中 |
| `binding-http/` | Declarative Binding 示例（active/shadow/shell） | 中 |
| `binding-openapi-e2e/` | OpenAPI 到 binding SKILL.md 的端到端流程 | 中 |
| `owlhub_skills/` | OwlHub 业务技能示例（监控/分析/工作流） | 中 |
| `integrations_llm/` | LLM 集成调用示例（基础调用/路由/function calling） | 中 |

## 快速开始

```bash
cd examples/simple-cron
poetry run python main.py
```
