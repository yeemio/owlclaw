# OwlClaw 配置系统说明

## 概览

OwlClaw 配置系统采用四层优先级合并：

1. 默认值（`owlclaw.config.models.OwlClawConfig`）
2. `owlclaw.yaml`
3. 环境变量（`OWLCLAW_` 前缀，`__` 作为嵌套分隔）
4. 运行时覆盖（`app.configure(...)`）

合并入口：`owlclaw.config.ConfigManager.load()`。

## 配置文件

可通过以下方式指定配置文件：

1. `OWLCLAW_CONFIG`
2. CLI 参数（各命令自行传入 `config`）
3. 当前目录 `./owlclaw.yaml`

默认模板可通过命令生成：

```bash
owlclaw init
```

模板路径：`templates/owlclaw.yaml`。

## 环境变量映射

格式：

```text
OWLCLAW_<SECTION>__<KEY>=<VALUE>
```

示例：

- `OWLCLAW_AGENT__HEARTBEAT_INTERVAL_MINUTES=30`
- `OWLCLAW_INTEGRATIONS__LLM__MODEL=gpt-4o-mini`
- `OWLCLAW_SECURITY__SANITIZER__ENABLED=false`

## 热更新

命令：

```bash
owlclaw reload
```

当前热更新白名单：

- `governance.*`
- `security.*`
- `triggers.*`
- `agent.heartbeat_interval_minutes`

冷更新字段会在 `reload` 报告中标记为 `skipped`（需重启生效）。

## 监听器

配置变更监听器注册入口：

- `register_governance_reload_listener()`
- `register_security_reload_listener()`
- `register_runtime_reload_listener()`

这些监听器用于在 `reload` 后刷新治理、安全与运行时心跳相关行为。

