# SPEC_TASKS_SCAN — OwlClaw 功能清单总览

> **来源**: `docs/ARCHITECTURE_ANALYSIS.md` §6.2 MVP 模块清单 + §9 下一步行动
> **角色**: Spec 循环的**单一真源**（Authority），所有 spec 的 tasks.md 必须映射到此清单
> **最后更新**: 2026-02-10

---

## 功能清单（从架构文档 §6.2 映射）

### Phase 0：仓库初始化

- [x] 清理 OwlClaw 仓库
- [x] 建立包结构（owlclaw / owlclaw-mcp）
- [x] pyproject.toml + MIT LICENSE + README
- [ ] 配置 CI（GitHub Actions: lint + test） → spec: ci-setup

### Phase 1：Agent 核心（MVP）

- [x] `owlclaw.capabilities.skills` — Skills 挂载（Agent Skills 规范，从应用目录加载 SKILL.md） → spec: capabilities-skills
- [x] `owlclaw.capabilities.registry` — 能力注册（@handler + @state 装饰器） → spec: capabilities-skills
- [ ] `owlclaw.agent.runtime` — Agent 运行时（SOUL.md 身份加载、记忆系统、Skills 知识注入） → spec: agent-runtime
- [ ] `owlclaw.agent.runtime` — function calling 决策循环（基于 litellm） → spec: agent-runtime
- [x] `owlclaw.agent.tools` — 内建工具（schedule_once、remember、recall、query_state） → spec: agent-tools
- [ ] `owlclaw.agent.heartbeat` — Heartbeat 机制（无事不调 LLM） → spec: agent-runtime
- [ ] `owlclaw.governance.visibility` — 能力可见性过滤（约束/预算/熔断/限流） → spec: governance
- [ ] `owlclaw.governance.ledger` — 执行记录 → spec: governance
- [ ] `owlclaw.governance.router` — task_type → 模型路由 → spec: governance
- [ ] `owlclaw.triggers.cron` — Cron 触发器 → spec: triggers-cron
- [ ] `owlclaw.integrations.hatchet` — Hatchet 直接集成（MIT，持久执行 + cron + 调度） → spec: integrations-hatchet
- [ ] `owlclaw.integrations.llm` — litellm 集成 → spec: integrations-llm
- [ ] mionyee 3 个任务端到端验证 → spec: e2e-validation
- [ ] 决策质量对比测试：v3 Agent vs 原始 cron → spec: e2e-validation

### Phase 2：扩展 + 可观测

- [ ] `owlclaw.triggers.webhook` — Webhook 触发器 → spec: triggers-webhook
- [ ] `owlclaw.triggers.queue` — 消息队列触发器 → spec: triggers-queue
- [ ] `owlclaw.integrations.langfuse` — Langfuse tracing → spec: integrations-langfuse
- [ ] `owlclaw.cli.scan` — AST 扫描器（自动生成 SKILL.md 骨架） → spec: cli-scan
- [ ] `owlclaw-mcp` — MCP Server（OpenClaw 通道，只读查询为主） → spec: mcp-server
- [ ] 非交易场景 examples（至少 2 个） → spec: examples

### Phase 3：开源发布

- [ ] PyPI 发布 owlclaw + owlclaw-mcp → spec: release
- [ ] GitHub 开源（MIT） → spec: release
- [ ] mionyee 完整接入示例 → spec: examples
- [ ] `owlclaw.cli.migrate` — AI 辅助迁移工具 → spec: cli-migrate
- [ ] 社区反馈收集 → spec: release
- [ ] 根据社区需求评估是否需要 Temporal 支持 → spec: release

---

## Spec 索引

| Spec 名称 | 路径 | 状态 | 覆盖模块 |
|-----------|------|------|---------|
| capabilities-skills | `.kiro/specs/capabilities-skills/` | ✅ 文档齐全 | skills + registry |
| agent-runtime | `.kiro/specs/agent-runtime/` | 待创建 | runtime + heartbeat + function calling |
| agent-tools | `.kiro/specs/agent-tools/` | ✅ 文档齐全 | 内建工具 |
| governance | `.kiro/specs/governance/` | 待创建 | visibility + ledger + router |
| triggers-cron | `.kiro/specs/triggers-cron/` | 待创建 | cron 触发器 |
| integrations-hatchet | `.kiro/specs/integrations-hatchet/` | ✅ 文档齐全 | Hatchet 集成 |
| integrations-llm | `.kiro/specs/integrations-llm/` | ✅ 文档齐全 | litellm 集成 |
| e2e-validation | `.kiro/specs/e2e-validation/` | 待创建 | mionyee 端到端验证 |
| triggers-webhook | `.kiro/specs/triggers-webhook/` | 待创建 | webhook 触发器 |
| triggers-queue | `.kiro/specs/triggers-queue/` | 待创建 | 消息队列触发器 |
| integrations-langfuse | `.kiro/specs/integrations-langfuse/` | 待创建 | Langfuse tracing |
| cli-scan | `.kiro/specs/cli-scan/` | 待创建 | AST 扫描器 |
| mcp-server | `.kiro/specs/mcp-server/` | 待创建 | owlclaw-mcp |
| examples | `.kiro/specs/examples/` | 待创建 | 示例 |
| cli-migrate | `.kiro/specs/cli-migrate/` | 待创建 | 迁移工具 |
| release | `.kiro/specs/release/` | 待创建 | PyPI + GitHub 发布 |
| ci-setup | `.kiro/specs/ci-setup/` | 待创建 | GitHub Actions CI |

---

## Checkpoint（供 Spec 循环使用）

| 字段 | 值 |
|------|---|
| 最后更新 | 2026-02-10 |
| 当前批次 | Phase 1 MVP spec 文档创建 |
| 批次状态 | 已完成 4 个 spec 文档（capabilities-skills、integrations-hatchet、integrations-llm、agent-tools） |
| 已完成项 | 3（Phase 0）+ 4 个 spec 文档 |
| 下一待执行 | 继续创建 Phase 1 剩余 spec 文档（agent-runtime、governance、triggers-cron） |
| 阻塞项 | 无 |
| 健康状态 | 正常 |
| 连续无进展轮数 | 0 |

---

## 使用说明

1. **Spec 循环**启动时，AI 从本文件的 Checkpoint 读取状态
2. 每轮循环完成后，AI 更新 Checkpoint 和对应的 `[ ]` → `[x]`
3. 功能清单须 ⊇ 各 spec 的 tasks.md 中的所有 task
4. 新增 spec 时须同步更新 Spec 索引表
5. 详细 Spec 循环流程见 `.cursor/rules/owlclaw_core.mdc` 第四节
