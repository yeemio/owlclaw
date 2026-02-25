# Tasks: 开源发布

## 文档联动

- requirements: `.kiro/specs/release/requirements.md`
- design: `.kiro/specs/release/design.md`
- tasks: `.kiro/specs/release/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **状态**：未开始  
> **预估工作量**：3-5 天  
> **最后更新**：2026-02-22  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选。

---

## 进度概览

- **总任务数**：15
- **已完成**：0
- **进行中**：0
- **未开始**：15

---

## 1. 包构建准备（1 天）

### 1.1 pyproject.toml 完善
- [x] 1.1.1 确认 owlclaw 包元数据完整（name, version, description, author, license, keywords, classifiers）
- [x] 1.1.2 配置可选依赖组（`[langchain]`, `[dev]`）
- [x] 1.1.3 配置 CLI 入口点（`owlclaw = "owlclaw.cli:main"`）
- [ ] 1.1.4 确认 owlclaw-mcp 包独立构建配置

### 1.2 敏感信息检查
- [x] 1.2.1 扫描仓库确认无硬编码 API key、token、密码
  - 基线扫描：`rg -n -S "AKIA|ASIA|BEGIN PRIVATE KEY|ghp_|sk-|xoxb-|xoxp-|xoxa-|xoxr-" owlclaw tests scripts .github docs`
  - 结果：仅测试样例/文档占位命中，未发现可用真实凭证
- [x] 1.2.2 确认 .gitignore 覆盖 .env、*.pyc、__pycache__、dist/、build/
- [x] 1.2.3 确认 .env.example 存在且不含真实凭证

---

## 2. 文档准备（1 天）

### 2.1 README.md（英文）
- [ ] 2.1.1 编写项目定位（一句话 + 详细描述）
- [ ] 2.1.2 编写 Quick Start（安装 → 创建 Skill → 运行第一个 Agent）
- [ ] 2.1.3 编写架构概览图（ASCII）
- [ ] 2.1.4 编写与 LangChain/LangGraph 的对比/互补关系
- [ ] 2.1.5 编写链接列表（文档、示例、贡献指南、许可证）

### 2.2 辅助文档
- [ ] 2.2.1 编写 CONTRIBUTING.md（开发环境搭建、测试运行、PR 规范、代码风格）
- [x] 2.2.2 编写 CHANGELOG.md（v0.1.0 初始版本记录）
- [x] 2.2.3 创建 GitHub Issue 模板（Bug Report、Feature Request）

---

## 3. 自动化发布（1 天）

### 3.1 GitHub Actions
- [ ] 3.1.1 创建 `.github/workflows/release.yml`（tag-triggered）
- [ ] 3.1.2 配置 PyPI token 到 GitHub Secrets
- [ ] 3.1.3 测试发布流程（先发布到 TestPyPI）

---

## 4. 发布执行（0.5 天）

### 4.1 首次发布
- [ ] 4.1.1 创建 Git tag `v0.1.0` 触发发布
- [ ] 4.1.2 验证 PyPI 安装：干净环境 `pip install owlclaw` 成功
- [ ] 4.1.3 验证 CLI：`owlclaw --version` 和 `owlclaw skill list` 正常
- [ ] 4.1.4 验证 GitHub Release 自动创建

---

## 5. 社区准备（0.5 天）

### 5.1 社区渠道
- [ ] 5.1.1 启用 GitHub Discussions
- [ ] 5.1.2 仓库设为 Public
- [ ] 5.1.3 添加 Topics 和 Description

---

## 6. 验收清单

### 6.1 功能验收
- [ ] `pip install owlclaw` 在干净环境中成功
- [ ] `owlclaw --version` 输出正确版本
- [ ] examples/ 中至少 1 个示例可独立运行
- [ ] GitHub Release 包含 changelog

### 6.2 文档验收
- [ ] README.md 英文完整
- [ ] CONTRIBUTING.md 可指导新贡献者
- [ ] CHANGELOG.md 记录 v0.1.0

---

## 7. 依赖与阻塞

### 7.1 依赖
- Phase 1 MVP 模块全部验收通过
- ci-setup spec 完成
- examples spec 至少 2 个非交易示例完成

### 7.2 阻塞
- 无（Phase 3 自然排序在 Phase 1/2 之后）

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
