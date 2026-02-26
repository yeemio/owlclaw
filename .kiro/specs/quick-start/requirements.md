# Quick Start 指南 — 需求文档

> **Spec**: quick-start
> **创建日期**: 2026-02-25
> **目标**: 让新用户在 10 分钟内从安装到看见 Agent 决策输出

---

## 背景

OwlClaw 代码完成度已超过 85%，但缺少一个能让新用户快速上手的入口文档。Quick Start 指南是降低"落地差距"的关键——用户应该能在不配置任何外部服务（PostgreSQL、Hatchet、LLM API Key）的情况下，通过 Lite Mode 体验完整的 Agent 决策流程。

## 功能需求

### FR-1: Quick Start 文档

- 文档路径：`docs/QUICK_START.md`
- 语言：中文为主，代码和命令用英文
- 目标读者：有 Python 经验的后端开发者
- 时间承诺：10 分钟内完成全部步骤

### FR-2: 内容结构

1. **前置条件**：Python >= 3.10，pip/poetry
2. **安装**：`pip install owlclaw`（或 `poetry add owlclaw`）
3. **创建项目目录**：skills 目录 + SKILL.md + SOUL.md
4. **编写 app.py**：使用 `OwlClaw.lite()` 创建应用
5. **注册 handler**：至少一个业务处理函数
6. **运行**：`python app.py`，看到 Agent 决策日志输出
7. **下一步**：指向完整文档和示例

### FR-3: 配套最小示例

- 路径：`examples/quick_start/`
- 包含：`app.py`、`skills/inventory-check/SKILL.md`、`SOUL.md`
- 可直接 `python examples/quick_start/app.py` 运行
- 使用 Lite Mode，零外部依赖

### FR-4: README 引用

- `README.md` 中添加 Quick Start 章节链接

## 非功能需求

- 文档中所有代码片段必须可运行（基于 Lite Mode）
- 不依赖任何外部服务
- 输出应包含可见的 Agent 决策日志（structlog 格式）

## 验收标准

1. 新用户按文档步骤操作，10 分钟内看到 Agent 决策输出
2. `examples/quick_start/app.py` 可直接运行，exit code 0（Ctrl+C 退出）
3. 文档无死链接
