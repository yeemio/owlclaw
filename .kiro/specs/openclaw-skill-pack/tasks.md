# OpenClaw Skill 包 — 任务清单

> **Spec**: openclaw-skill-pack
> **阶段**: Phase 8.2
> **前置**: mcp-capability-export（MCP Server 工具就绪后才能打包）

---

## Task 0：Spec 文档与契约

- [x] 0.1 requirements.md / design.md / tasks.md 三层齐全
- [x] 0.2 与 SPEC_TASKS_SCAN.md Phase 8.2 对齐

## Task 1：Skill 包开发

- [x] 1.1 创建 `owlclaw-for-openclaw/` 目录结构
- [x] 1.2 编写主 SKILL.md（兼容 Agent Skills 规范）
- [x] 1.3 编写子 Skills（governance.md / persistent-tasks.md / business-connect.md）
- [x] 1.4 编写示例（budget-control.md / background-task.md / database-connect.md）
- [x] 1.5 编写 README.md（安装说明 + 快速上手）
- [x] 1.6 编写 OpenClaw 配置示例（owlclaw.example.json）

## Task 2：兼容性验证

- [ ] 2.1 在 OpenClaw 最新稳定版中测试 SKILL.md 解析
- [x] 2.2 验证 `owlclaw:` 扩展字段不影响 OpenClaw 解析
- [ ] 2.3 验证 OpenClaw Agent 能正确发现和调用 OwlClaw MCP 工具

## Task 3：ClawHub 发布

- [x] 3.1 Fork `openclaw/clawhub` 仓库
- [x] 3.2 添加 `owlclaw-for-openclaw/` 到 ClawHub
- [ ] 3.3 提交 PR 并通过审核
- [ ] 3.4 验证 Skill 包在 ClawHub 可搜索、可安装

## Task 4：教程编写

- [x] 4.1 编写教程："How to connect OpenClaw to your business database in one command"
- [x] 4.2 教程可复现性验证（从零开始跟教程走一遍）
- [x] 4.3 准备中文版教程（掘金/V2EX 发布用）

## Task 5：验收

- [ ] 5.1 Skill 包在 ClawHub 可安装
- [ ] 5.2 安装步骤 ≤ 3 步
- [ ] 5.3 教程 ≤ 10 分钟可完成
- [ ] 5.4 Phase 2 结束时评估下载量（止损线：< 100 则启动 Plan B）
