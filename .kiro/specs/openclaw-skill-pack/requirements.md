# OpenClaw Skill 包 — 需求文档

> **Spec**: openclaw-skill-pack
> **阶段**: Phase 8.2
> **决策来源**: `docs/DUAL_MODE_ARCHITECTURE_DECISION.md` D12 (OpenClaw 切入策略)
> **前置**: mcp-capability-export spec, skill-templates spec ✅

---

## 1. 背景

OpenClaw 的 ClawHub 每天有 15,000 次安装，800+ 活跃开发者。OwlClaw 通过发布 `owlclaw-for-openclaw` Skill 包切入这个生态，让 OpenClaw 用户无需了解 OwlClaw 的内部架构，直接获得治理、持久任务、业务接入能力。

## 2. User Stories

### US-1：Skill 包安装
**作为** OpenClaw 用户，**我希望** 通过 ClawHub 一键安装 `owlclaw-for-openclaw` Skill 包，**以便** 获得 OwlClaw 的能力。

**验收标准**：
- [ ] Skill 包在 ClawHub 可搜索、可安装
- [ ] 安装后 OpenClaw 自动发现 OwlClaw MCP Server 工具
- [ ] 安装步骤 ≤ 3 步（install → configure endpoint → use）

### US-2：SKILL.md 兼容性
**作为** OpenClaw 用户，**我希望** OwlClaw 的 SKILL.md 在 OpenClaw 中正常工作，**以便** 无缝使用。

**验收标准**：
- [ ] OwlClaw 的 SKILL.md 格式与 OpenClaw 的 Agent Skills 规范兼容
- [ ] OpenClaw Agent 能正确解析 OwlClaw SKILL.md 中的工具描述
- [ ] `owlclaw:` 扩展字段不影响 OpenClaw 的解析

### US-3：教程可复现
**作为** OpenClaw 用户，**我希望** 有一篇清晰的教程教我如何使用 OwlClaw Skill 包，**以便** 快速上手。

**验收标准**：
- [ ] 教程从安装到看到效果 ≤ 10 分钟
- [ ] 教程中的每一步都可复现
- [ ] 教程解决一个具体痛点（如"如何让 OpenClaw 安全连接你的业务系统"）

## 3. 非功能需求

- **兼容性**：支持 OpenClaw 最新稳定版
- **大小**：Skill 包体积 < 1MB
- **文档**：README 清晰，包含快速上手和常见问题

## 4. Definition of Done

- [ ] `owlclaw-for-openclaw` Skill 包发布到 ClawHub
- [ ] Skill 包可安装、可使用
- [ ] SKILL.md 兼容性测试通过
- [ ] 教程可复现
- [ ] ClawHub 有下载量（Phase 2 结束时评估）
