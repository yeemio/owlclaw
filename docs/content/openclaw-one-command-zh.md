# 一条命令把 OpenClaw 接到你的业务数据库

本文目标：让 OpenClaw 在 3 步内接入 OwlClaw MCP 能力。

1. 安装 Skill 包
2. 配置一个端点
3. 直接调用治理与持久任务工具

预计耗时：10 分钟内。

## 你会解决什么问题

OpenClaw 在业务落地里常见痛点：

- 看不到 AI 调用预算与审计轨迹
- 后台任务不够持久
- 业务 API 暴露为工具流程繁琐

`owlclaw-for-openclaw` 通过 MCP 打包解决以上问题。

## 第一步：安装 Skill 包

在 ClawHub 安装 `owlclaw-for-openclaw`。

本仓库中的包目录：

- `skills/owlclaw-for-openclaw/`

## 第二步：配置一个 MCP 端点

设置环境变量：

```bash
export OWLCLAW_MCP_ENDPOINT=http://127.0.0.1:8080/mcp
```

配置样例（可直接复用）：

```json
{
  "mcpServers": {
    "owlclaw": {
      "transport": "http",
      "url": "${OWLCLAW_MCP_ENDPOINT}",
      "agentCardUrl": "http://127.0.0.1:8080/.well-known/agent.json"
    }
  }
}
```

## 第三步：在 OpenClaw 里直接使用

可直接输入：

- “查询租户 `t-1`、代理 `openclaw-agent` 的预算状态”
- “创建一个 `nightly_sync` 后台任务”
- “查询 `<task_id>` 的执行状态”

预期结果：

- OpenClaw 自动发现 `governance_*` 与 `task_*` 工具
- 调用通过 OwlClaw MCP 执行并返回结果

## 复现验证记录

本教程步骤已通过仓库自动化测试验证：

- `tests/integration/test_mcp_openclaw_e2e_acceptance.py`
- `tests/integration/test_openclaw_skill_compatibility.py`
- `tests/unit/test_openclaw_skill.py`

验证日期：2026-02-28。
