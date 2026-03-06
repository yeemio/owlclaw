# Workflow Control Guide

## 目的

这套控制流用于在本机同时驱动 6 个工作窗口：

- `main`：统筹，使用 `codex`
- `review`：审校，使用 `claude`
- `codex`：编码，使用 `agent`
- `codex-gpt`：编码，使用 `agent`
- `audit-a`：深度审计，使用 `agent`
- `audit-b`：审计复核，使用 `agent`

控制器不会长期无脑发命令。它会参考 `.kiro/runtime/` 下的 mailbox、ack、heartbeat 状态，只在任务变化、停滞或阻塞时催办。

---

## 固定话术

当前固定话术以这 6 条为准：

- `main` -> `统筹`
- `review` -> `继续审校`
- `codex` -> `继续spec循环` 或 `继续`
- `codex-gpt` -> `继续spec循环` 或 `继续`
- `audit-a` -> `继续深度审计`
- `audit-b` -> `继续审计复核`

说明：

- `codex` / `codex-gpt` 在 `wait_for_review`、`wait_for_assignment`、`cleanup_or_commit_local_changes` 这类状态下会收到 `继续spec循环`
- 其余编码推进状态会收到 `继续`

---

## 启动方式

推荐直接用一键启动器：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout
```

这会启动：

- `owlclaw-main`
- `owlclaw-review`
- `owlclaw-codex`
- `owlclaw-codex-gpt`
- `owlclaw-audit-a`
- `owlclaw-audit-b`
- `owlclaw-control`

并且会自动为：

- `audit-a`
- `audit-b`

写入初始 `audit-state=idle`，所以审计窗口不再需要先手工建状态文件。

如果你希望降低批量起窗时的丢窗概率，可以加大间隔：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout -LaunchSpacingMilliseconds 2000
```

如果你确认布局稳定，再去尝试默认平铺；如果当前目标是“先用起来”，建议保持 `-SkipLayout`。

---

## 控制窗口

控制窗口脚本：

```powershell
pwsh ./scripts/workflow-terminal-control-console.ps1
```

支持命令：

- `help`
- `pause`
- `resume`
- `status`
- `send <agent>`
- `takeover <agent>`
- `quit`

示例：

```text
send review
takeover codex
pause
resume
status
```

---

## 自动催办逻辑

控制器默认不是固定盲发，而是看这些 runtime 文件：

- `.kiro/runtime/mailboxes/*.json`
- `.kiro/runtime/acks/*.json`
- `.kiro/runtime/heartbeats/*.json`
- `.kiro/runtime/audit-state/*.json`
- `.kiro/runtime/terminal-windows.json`

触发发送的典型条件：

- mailbox 指纹变化
- ack 缺失
- heartbeat 缺失
- ack 过旧
- heartbeat 过旧
- ack 状态为 `blocked`
- ack 状态为 `idle`

不触发发送的典型条件：

- mailbox 没变化
- ack/heartbeat 都是新鲜的
- 当前 agent 没有进入停滞态

默认停滞阈值由控制台脚本传入，当前默认是 `180` 秒。

### 审计状态协议

`audit-a` / `audit-b` 不再是“无状态角色”。它们应主动写自己的状态文件：

```powershell
poetry run python scripts/workflow_audit_state.py update --agent audit-a --status started --finding-ref D48 --summary "reviewing finding batch"
poetry run python scripts/workflow_audit_state.py update --agent audit-b --status blocked --finding-ref D49 --note "need human confirmation"
```

查看当前状态：

```powershell
poetry run python scripts/workflow_audit_state.py show --agent audit-a --json
```

控制器对审计窗口的行为：

- 没有 `audit-state` 文件：静默，不自动催
- `updated_at` 过旧：催办
- `status=blocked` 或 `status=idle`：催办
- 状态新鲜：不催

---

## 人工接管

当某个窗口需要人手接管时：

```text
takeover <agent>
```

例如：

```text
takeover review
takeover codex-gpt
```

接管后，控制器会尝试优先按 `HWND` 聚焦窗口；如果句柄不可用，再回退到 PID 或标题。
控制器在发送失败时也会尝试重新扫描顶层窗口并刷新 manifest，避免窗口句柄漂移后永久失联。

如果你只想临时暂停自动催办：

```text
pause
```

恢复：

```text
resume
```

---

## 常见问题

### 1. 只有 `main` 在工作，其它窗口没有反应

先看这几个事实：

- `main` 一般最稳定，因为 `codex` 会保持窗口标题
- `review` 可能把标题改成 `claude`
- `agent` / `claude` / `codex` 的窗口行为不完全一致

处理顺序：

1. 先关闭当前这批旧窗口
2. 用新版启动器重新拉起：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout -LaunchSpacingMilliseconds 2000
```

3. 再观察控制窗口

不要在旧窗口上持续叠加测试，因为 `.kiro/runtime/terminal-windows.json` 是按启动时窗口句柄生成的。

### 2. 控制器一直刷屏

新版控制器已经降噪，只会在这些情况输出：

- 真正发出命令
- 发现停滞
- 发现缺 heartbeat / ack
- 手工执行 `status`

如果你看到的仍是旧版刷屏行为，直接关掉旧控制窗口，重新运行：

```powershell
pwsh ./scripts/workflow-terminal-control-console.ps1
```

### 3. `claude` 经常弹 `Run this command?`

这不是统筹器本身的逻辑，而是 `claude` 的 shell allowlist 在拦。

当前本地仓库配置 [settings.local.json](D:/AI/owlclaw/.claude/settings.local.json) 已经放开常见命令：

- `Shell(cd:*)`
- `Shell(poetry:*)`
- `Shell(pytest:*)`
- `Shell(git:*)`
- `Shell(python:*)`
- `Shell(pwsh:*)`

如果旧 `claude` 会话仍然弹窗，通常需要重开该会话，让它重新读取本地设置。

### 4. `review` 找不到窗口

控制器会优先尝试：

1. `owlclaw-review`
2. `claude`

所以 `review` 不一定必须保持 `owlclaw-review` 这个标题。

### 5. 想手工强制发一次

用：

```text
send <agent>
```

例如：

```text
send main
send review
send audit-b
```

这会绕过自动停滞判断，立即发一次当前固定话术。

---

## 相关文件

- [workflow-launch.ps1](/D:/AI/owlclaw/scripts/workflow-launch.ps1)
- [workflow-terminal-control-console.ps1](/D:/AI/owlclaw/scripts/workflow-terminal-control-console.ps1)
- [workflow_terminal_control.py](/D:/AI/owlclaw/scripts/workflow_terminal_control.py)
- [workflow_sendkeys.ps1](/D:/AI/owlclaw/scripts/workflow_sendkeys.ps1)
- [workflow_focus_window.ps1](/D:/AI/owlclaw/scripts/workflow_focus_window.ps1)
- [settings.local.json](/D:/AI/owlclaw/.claude/settings.local.json)
