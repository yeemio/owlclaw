# Tasks: 开源发布

## 文档联动

- requirements: `.kiro/specs/release/requirements.md`
- design: `.kiro/specs/release/design.md`
- tasks: `.kiro/specs/release/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **状态**：进行中  
> **预估工作量**：3-5 天  
> **最后更新**：2026-02-26  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选。

---

## 进度概览

- **总任务数**：32
- **已完成**：27
- **进行中**：0
- **未开始**：5

---

## 1. 包构建准备（1 天）

### 1.1 pyproject.toml 完善
- [x] 1.1.1 确认 owlclaw 包元数据完整（name, version, description, author, license, keywords, classifiers）
- [x] 1.1.2 配置可选依赖组（`[langchain]`, `[dev]`）
- [x] 1.1.3 配置 CLI 入口点（`owlclaw = "owlclaw.cli:main"`）
- [x] 1.1.4 确认 owlclaw-mcp 包独立构建配置

### 1.2 敏感信息检查
- [x] 1.2.1 扫描仓库确认无硬编码 API key、token、密码
  - 基线扫描：`rg -n -S "AKIA|ASIA|BEGIN PRIVATE KEY|ghp_|sk-|xoxb-|xoxp-|xoxa-|xoxr-" owlclaw tests scripts .github docs`
  - 结果：仅测试样例/文档占位命中，未发现可用真实凭证
- [x] 1.2.2 确认 .gitignore 覆盖 .env、*.pyc、__pycache__、dist/、build/
- [x] 1.2.3 确认 .env.example 存在且不含真实凭证

---

## 2. 文档准备（1 天）

### 2.1 README.md（英文）
- [x] 2.1.1 编写项目定位（一句话 + 详细描述）
- [x] 2.1.2 编写 Quick Start（安装 → 创建 Skill → 运行第一个 Agent）
- [x] 2.1.3 编写架构概览图（ASCII）
- [x] 2.1.4 编写与 LangChain/LangGraph 的对比/互补关系
- [x] 2.1.5 编写链接列表（文档、示例、贡献指南、许可证）

### 2.2 辅助文档
- [x] 2.2.1 编写 CONTRIBUTING.md（开发环境搭建、测试运行、PR 规范、代码风格）
- [x] 2.2.2 编写 CHANGELOG.md（v0.1.0 初始版本记录）
- [x] 2.2.3 创建 GitHub Issue 模板（Bug Report、Feature Request）

---

## 3. 自动化发布（1 天）

### 3.1 GitHub Actions
- [x] 3.1.1 创建 `.github/workflows/release.yml`（tag-triggered）
- [ ] 3.1.2 配置 PyPI token 到 GitHub Secrets
  - 状态补充（2026-02-25）：`gh secret list -R yeemio/owlclaw` 未返回 `PYPI_TOKEN/TEST_PYPI_TOKEN`，需维护者在仓库 Actions Secrets 补齐。
  - 状态补充（2026-02-26）：再次核验 `gh secret list -R yeemio/owlclaw` 仍为空，发布凭据仍未配置。
- [ ] 3.1.3 测试发布流程（先发布到 TestPyPI）
  - 状态补充（2026-02-25）：workflow_dispatch run `22404173746` 执行到 TestPyPI 发布阶段后返回 `HTTP 403 Forbidden`，日志显示 `TWINE_PASSWORD` 为空，根因仍是 3.1.2 未完成。
  - 状态补充（2026-02-26）：workflow_dispatch run `22433883650` 再次失败于 `Publish to TestPyPI`，日志仍显示 `TWINE_PASSWORD` 为空并返回 `HTTP 403 Forbidden`。

---

## 4. 发布执行（0.5 天）

### 4.1 首次发布
- [ ] 4.1.1 创建 Git tag `v0.1.0` 触发发布
  - 状态补充（2026-02-26）：当前编码 worktree 无主分支发布权限；需维护者在 `main` 执行正式 tag 创建并触发 Release workflow。
- [ ] 4.1.2 验证 PyPI 安装：干净环境 `pip install owlclaw` 成功
  - 远程核验（2026-02-25）：临时虚拟环境执行 `pip install owlclaw` 返回 `No matching distribution found`，说明尚未发布到 PyPI
- [x] 4.1.3 验证 CLI：`owlclaw --version` 和 `owlclaw skill list` 正常  
  - 本地验证（2026-02-25）：`poetry run owlclaw --version` → `owlclaw 0.1.0`；`poetry run owlclaw skill list` 正常输出
- [x] 4.1.4 验证 GitHub Release 自动创建
  - 远程核验（2026-02-26）：release run `22433883650` 在失败前已由 semantic-release 自动创建 `v1.2.0`，`gh release view v1.2.0` 可见发布时间 `2026-02-26T08:27:41Z`。

---

## 5. 社区准备（0.5 天）

### 5.1 社区渠道
- [x] 5.1.1 启用 GitHub Discussions  
  - 远程核验（2026-02-25）：`gh api repos/yeemio/owlclaw` 返回 `has_discussions=true`
- [x] 5.1.2 仓库设为 Public  
  - 远程核验（2026-02-25）：`gh repo view yeemio/owlclaw --json visibility` 返回 `PUBLIC`
- [x] 5.1.3 添加 Topics 和 Description  
  - 远程核验（2026-02-25）：`gh repo view yeemio/owlclaw --json repositoryTopics,description` 返回非空 topics + description

---

## 6. 验收清单

### 6.1 功能验收
- [ ] `pip install owlclaw` 在干净环境中成功
  - 状态补充（2026-02-26）：与 4.1.2 绑定，等待 TestPyPI/PyPI 发布成功后复验。
- [x] `owlclaw --version` 输出正确版本
- [x] examples/ 中至少 1 个示例可独立运行
- [x] GitHub Release 包含 changelog
  - 远程核验（2026-02-26）：`gh release view v1.2.0` 的 release body 包含版本标题 `## v1.2.0 (2026-02-26)` 与分组变更日志条目。

### 6.2 文档验收
- [x] README.md 英文完整
- [x] CONTRIBUTING.md 可指导新贡献者
- [x] CHANGELOG.md 记录 v0.1.0

---

## 7. 依赖与阻塞

### 7.1 依赖
- Phase 1 MVP 模块全部验收通过
- ci-setup spec 完成
- examples spec 至少 2 个非交易示例完成

### 7.2 阻塞
- 外部平台操作待执行（非仓内可自动完成）：
  - GitHub Secrets：`PYPI_TOKEN` / `TEST_PYPI_TOKEN`
  - TestPyPI 实际发布验证
  - PyPI 发布后安装验收（`pip install owlclaw`）
  - 本轮核验（2026-02-26）：`gh auth status` 正常；`gh secret list -R yeemio/owlclaw` 仍无发布凭据；release run `22433883650` 在 `Publish to TestPyPI` 以 `HTTP 403 Forbidden` 失败（`TWINE_PASSWORD` 为空）；GitHub Release 自动创建已验证（`v1.2.0`）。

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-26
