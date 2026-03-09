# Workflow Control Guide

## 目的

这套控制流用于在本机同时驱动 6 个工作窗口：

- `main`：统筹，使用 `codex`
- `review`：审校，使用 `claude`
- `codex`：编码，使用 `agent`
- `codex-gpt`：编码，使用 `agent`
- `audit-a`：深度审计，使用 `agent`
- `audit-b`：审计复核，使用 `agent`

角色真源配置文件：

- [.kiro/workflow_terminal_config.json](/D:/AI/owlclaw/.kiro/workflow_terminal_config.json)

以后如果要调整目录、CLI 类型、窗口标题、固定话术，优先改这一个 JSON，再让启动器和控制器读取它。

控制器不会长期无脑发命令。它会参考 `.kiro/runtime/` 下的 mailbox、ack、heartbeat，以及 mailbox 里绑定的 `object_type/object_id`，只在任务变化、停滞或阻塞时催办。

每个 agent 现在还会在 mailbox 中持续收到自己的“岗位合同”：

- `role_title`
- `role_contract`
- `must_do`
- `must_not_do`

也就是每一轮都重复告诉它“你是谁、该做什么、不能做什么”，不再只靠一句短提示词。

---

## 固定话术

当前固定话术以这 6 条为准：

- `main` -> `统筹`
- `review` -> `继续审校`
- `codex` -> `继续spec循环` 或 `继续`
- `codex-gpt` -> `继续spec循环` 或 `继续`
- `audit-a` -> `继续深度审计`
- `audit-b` -> `继续审计复核`

其中两条审计话术现在不是“空口号”，而是强约束提示：

- `audit-a` 必须按 `deep-codebase-audit` skill 做多维度代码审计，不能只读文档，不能改代码，只能提交 structured findings 给 `main`
- `audit-b` 必须按同一 skill 做独立复核，重新读代码验证并继续找漏项，不能只复述已有报告，不能改代码

说明：

- `main` 在 `monitor`、`clean_local_changes`、`merge_review_work`、`assign_next_batch`、`process_triage`、`process_verdict` 这些统筹状态下都会收到 `统筹`
- `review` 在 `review_pending_commits`、`idle`、`review_delivery` 状态下都会收到 `继续审校`
- `codex` / `codex-gpt` 在 `wait_for_review`、`wait_for_assignment`、`cleanup_or_commit_local_changes`、`execute_assignment` 状态下会收到 `继续spec循环`
- 这样 6 个窗口不会因为进入“等待态/监控态”而整体停转

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

默认 6 个角色窗口现在是 observer 视图，不直接往 CLI 注入输入，因此不会抢鼠标、焦点或剪贴板。每个窗口会持续展示：

- 当前 mailbox / stage / object
- 最近一次 executor 结果
- 最近一条 assistant 输出
- 最近相关 workflow 对象（finding / triage / assignment / verdict / delivery / blocker）
- 最近 supervisor / execution 日志

默认情况下，`owlclaw-control` 运行的是 `workflow-supervisor-console.ps1`，也就是无头执行链的前台观察窗口。

如果你要显式使用旧的窗口催办控制台，才额外加：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout -UseTerminalController
```

这时 `owlclaw-control` 会运行 `workflow-terminal-control-console.ps1`。默认是 observe-only，不会抢鼠标、焦点和剪贴板；只有显式加 `-EnableSendKeys` 才会启用旧的窗口注入链路。

默认的 supervisor 控制台用于观察闭环主链：

- `workflow_orchestrator.py`
- `workflow_agent.py`
- `workflow_executor.py`

并且会自动为：

- `audit-a`
- `audit-b`

写入初始 `audit-state=idle`，所以审计窗口不再需要先手工建状态文件。
同时会在后台启动审计状态心跳，持续刷新 `audit-a` / `audit-b` 的 `updated_at`。

如果你希望降低批量起窗时的丢窗概率，可以加大间隔：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout -LaunchSpacingMilliseconds 2000
```

新版启动器是串行启动，不是一次性全开：

- 先启动一个角色窗口
- 写入 `.kiro/runtime/launch-state/<agent>.json`
- 只有当该角色进入 `running`，才继续启动下一个
- 如果某个角色很快退回 PowerShell，启动器会判定为失败并默认中止后续启动
- 对 `agent` / `claude` / `codex` 的瞬时启动失败会自动短重试，并把输出落到 `.kiro/runtime/launch-logs/<agent>.log`

如果你想在某个角色失败后继续把剩余窗口也拉起来，再额外加：

```powershell
pwsh ./scripts/workflow-launch.ps1 -SkipLayout -ContinueOnLaunchFailure
```

查看某个角色的启动状态：

```powershell
poetry run python scripts/workflow_launch_state.py --repo-root D:\AI\owlclaw show --agent codex --json
```

查看某个角色的启动日志：

```powershell
Get-Content .kiro\runtime\launch-logs\codex.log
```

如果你确认布局稳定，再去尝试默认平铺；如果当前目标是“先用起来”，建议保持 `-SkipLayout`。

---

## 控制窗口

默认控制窗口脚本：

```powershell
pwsh ./scripts/workflow-supervisor-console.ps1
```

旧的窗口催办控制台：

```powershell
pwsh ./scripts/workflow-terminal-control-console.ps1
```

如果你明确接受窗口激活和剪贴板注入，再显式开启：

```powershell
pwsh ./scripts/workflow-terminal-control-console.ps1 -EnableSendKeys
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
- `.kiro/runtime/findings/`、`triage/`、`assignments/`、`deliveries/`、`verdicts/`、`merges/`、`blockers/`
- `.kiro/runtime/audit-state/*.json`
- `.kiro/runtime/terminal-windows.json`

触发发送的典型条件：

- mailbox 指纹变化（包括 `object_type/object_id` 变化）
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

推荐同时回写本轮真实阅读范围：

```powershell
poetry run python scripts/workflow_audit_state.py update --agent audit-a --status started --summary "auditing runtime" --file-read owlclaw/agent/runtime/runtime.py --dimension-covered core_logic --lines-read 400
```

提交审计 finding 时，必须带代码证据、文件路径、审计维度和 thinking lens：

```powershell
poetry run python scripts/workflow_audit_state.py finding --agent audit-a --title "Observation tool leaks unsanitized args" --summary "Tool output flows into prompt without sanitizer." --severity p1 --spec workflow-closed-loop --task-ref 3.3 --target-agent codex --target-branch codex-work --file owlclaw/agent/runtime/runtime.py --dimension core_logic --lens adversary --evidence "Traced tool result into runtime._build_messages() without sanitizer."
```

缺少这些字段的 audit finding 会被协议层拒绝，避免“只看文档”的假审计进入主链。

查看当前状态：

```powershell
poetry run python scripts/workflow_audit_state.py show --agent audit-a --json
```

控制器对审计窗口的行为：

- 没有 `audit-state` 文件：静默，不自动催
- `updated_at` 过旧：催办
- `status=blocked`：催办
- 首次启动且 `status=idle`：会先催一次，避免审计窗口冷启动静默
- `status=idle` 且状态新鲜、且刚刚催过：不重复催
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

注意：

- `workflow-supervisor-console.ps1` 不会抢占鼠标和剪贴板
- `workflow-terminal-control-console.ps1` 默认仅记录 observe 状态，不做窗口注入
- 只有 `-EnableSendKeys` 时，才会调用 `workflow_sendkeys.ps1` 激活窗口并粘贴固定话术

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
