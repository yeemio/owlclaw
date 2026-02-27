# OpenClaw Skill 包 — 设计文档

> **Spec**: openclaw-skill-pack
> **阶段**: Phase 8.2

---

## 1. Skill 包结构

```
owlclaw-for-openclaw/
├── SKILL.md                    # 主 Skill 描述（兼容 Agent Skills 规范）
├── README.md                   # 安装和使用说明
├── skills/
│   ├── governance.md           # 治理能力 Skill
│   ├── persistent-tasks.md     # 持久任务 Skill
│   └── business-connect.md     # 业务系统连接 Skill
├── examples/
│   ├── budget-control.md       # 预算控制示例
│   ├── background-task.md      # 后台任务示例
│   └── database-connect.md     # 数据库连接示例
└── config/
    └── owlclaw.example.json    # OpenClaw 配置示例
```

## 2. SKILL.md 兼容性设计

OwlClaw 的 SKILL.md 使用 `owlclaw:` 扩展字段。OpenClaw 的 Agent Skills 规范允许自定义扩展字段（忽略未知字段）。

```yaml
---
name: owlclaw-governance
description: AI call governance - budget, rate limiting, circuit breaking
version: 0.1.0
owlclaw:
  binding:
    type: mcp
    endpoint: ${OWLCLAW_MCP_ENDPOINT}
---
```

OpenClaw 解析时忽略 `owlclaw:` 字段，读取 `name`、`description`、`tools` 等标准字段。

## 3. 安装流程

```
Step 1: 安装 Skill 包
  → OpenClaw UI: Browse ClawHub → Search "owlclaw" → Install

Step 2: 配置 OwlClaw 端点
  → 设置环境变量 OWLCLAW_MCP_ENDPOINT=http://localhost:8080
  → 或在 OpenClaw 配置中添加 MCP Server 连接

Step 3: 使用
  → OpenClaw Agent 自动发现 OwlClaw 工具
  → 用户可以说"查看我的 AI 调用预算"、"创建一个后台任务"等
```

## 4. ClawHub 发布

遵循 ClawHub 的发布流程：
1. Fork `openclaw/clawhub` 仓库
2. 添加 `owlclaw-for-openclaw/` 目录
3. 提交 PR，通过 ClawHub 审核
4. 合并后自动出现在 ClawHub 搜索结果中

## 5. 教程设计

教程标题方向："How to connect OpenClaw to your business database in one command"

结构：
1. 问题（OpenClaw 连接业务系统太难）
2. 解决方案（OwlClaw Skill 包 + `owlclaw migrate`）
3. 步骤（安装 → 配置 → 运行 → 看到效果）
4. 结果（截图/输出对比）
5. 下一步（更多能力：治理、持久任务）

## 6. 测试策略

- **兼容性测试**：OwlClaw SKILL.md 在 OpenClaw 中解析正确
- **安装测试**：Skill 包在 ClawHub 可安装
- **端到端测试**：安装后 OpenClaw Agent 能调用 OwlClaw 工具
- **教程测试**：教程每一步可复现
