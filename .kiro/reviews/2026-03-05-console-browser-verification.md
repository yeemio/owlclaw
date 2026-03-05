# OwlClaw Console 浏览器验证报告（Phase 14 / codex-gpt-work）

> **执行日期**：2026-03-05  
> **Spec**：`console-browser-real-e2e`（Task 2.1~2.3）  
> **执行范围**：真实环境脚本 + 手工维度（WS/效果/可访问性）  
> **证据目录**：`.kiro/reviews/artifacts/2026-03-05-console-browser/`

---

## 一、执行摘要

| 项目 | 结果 | 说明 |
|------|------|------|
| 真实环境启动脚本强化 | ✅ 完成 | `scripts/console-local-setup.ps1` 增加参数化、健康检查、可选 E2E、日志落盘 |
| 手工维度执行（可 CLI 复现实项） | ✅ 完成 | 已执行 `/healthz` 与关键 API/降级链路并固化输出 |
| 失败项与复现步骤记录 | ✅ 完成 | M-1（WS 404）与 M-2（`start-server-and-test` 缺失）已归档 |

---

## 二、执行步骤与证据

### 2.1 服务启动与健康检查

- 启动命令（后台）：`poetry run owlclaw start --port 8000`
- 健康检查：`GET /healthz` 返回 200
- 证据：
  - `.kiro/reviews/artifacts/2026-03-05-console-browser/api-checks.json`

### 2.2 手工维度（API/降级/WS 入口）

| 检查项 | 结果 | 摘要 |
|--------|------|------|
| `/api/v1/overview` | ✅ | 200；db/llm/langfuse 处于可预期降级状态 |
| `/api/v1/agents` | ✅ | 200；`items=[]` 且 `message=Database not configured` |
| `/api/v1/agents/demo-agent` | ✅ | 404（预期） |
| `/api/v1/governance/budget` | ✅ | 200；空 items 正常返回 |
| `/api/v1/ledger?order_by=invalid` | ✅ | 422（契约错误码） |
| `/api/v1/triggers` | ✅ | 200；空列表降级 |
| `/api/v1/triggers/demo/history` | ✅ | 200；分页空数据 |
| `/api/v1/settings` | ✅ | 200；runtime/mcp/database/owlhub/system 字段完整 |
| `/api/v1/ws` | ⚠️ | 404（见失败项 M-1） |

---

## 三、失败项与复现步骤

### M-1：WS 手工验证阻塞（/api/v1/ws 返回 404）

- 复现步骤：
1. `poetry run owlclaw start --port 8000`
2. 请求 `http://127.0.0.1:8000/api/v1/ws`
- 实际：HTTP 404
- 影响：无法在当前环境完成 WS 消息类型手工验收（N-8）
- 建议：审校阶段在具备 WS 依赖的环境复验 N-7/N-8。

### M-2：前端一键 E2E 命令阻塞（缺少 start-server-and-test）

- 复现步骤：
1. `cd owlclaw/web/frontend`
2. `npm run test:e2e`
- 实际：`start-server-and-test is not recognized`
- 复现输出（摘录）：
  - `> owlclaw-console-frontend@0.0.0 test:e2e`
  - `> start-server-and-test server http://127.0.0.1:8000/healthz test:e2e:run`
  - `'start-server-and-test' is not recognized as an internal or external command`
- 影响：一键链路不可用；需改用手动启动服务 + `npm run test:e2e:run`
- 建议：执行 `npm install` 补齐依赖，或改脚本统一走 `test:e2e:run`。

---

## 四、结论（codex-gpt-work 范围）

- Task 2.1：✅  
- Task 2.2：✅（CLI 可执行手工项已完成）  
- Task 2.3：✅  

**移交给 review-work**：  
请结合 codex-work 的 Playwright 主路径结果，统一给出 `PASS / CONDITIONAL_PASS / FAIL` 放行结论。

---

## 五、审校输入摘要（Review-work 快速执行）

### 5.1 本分支已交付边界

1. 已完成 Task 2.1~2.3（脚本强化 + 手工维度 + 失败复现）。
2. 已回写 spec 状态：
   - `.kiro/specs/console-browser-real-e2e/tasks.md`
   - `.kiro/specs/SPEC_TASKS_SCAN.md`
3. 证据主文件：
   - `.kiro/reviews/artifacts/2026-03-05-console-browser/api-checks.json`

### 5.2 仍待完成（非本分支范围）

1. `codex-work`：Task 1.1~1.4（Playwright 主路径 + 网络参数断言 + 自动化摘要）
2. `review-work`：Task 3.1~3.3（证据完整性审查 + 高风险复核 + 放行结论）
3. 最终验收：Task 4.1~4.3

### 5.3 Reviewer 快速命令

```powershell
pwsh -File scripts/console-local-setup.ps1 -SkipDbInit -SkipMigrate
Get-Content .kiro/reviews/artifacts/2026-03-05-console-browser/api-checks.json
Get-Content .kiro/reviews/2026-03-05-console-browser-verification.md
```

### 5.4 放行提示

1. M-1 / M-2 属于环境与工具链阻塞，不是后端契约回退。  
2. 若 codex-work 自动化证据齐全且高风险项无新增故障，可评估 `CONDITIONAL_PASS`，并保留 WS 复验后续动作。
