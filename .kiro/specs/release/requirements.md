# Requirements: 开源发布

> **目标**：将 OwlClaw 核心包和 MCP Server 发布到 PyPI，并在 GitHub 公开开源（MIT 许可证）  
> **优先级**：P3（Phase 3）  
> **预估工作量**：3-5 天

---

## 1. 背景与动机

### 1.1 当前问题

OwlClaw 目前是私有仓库开发阶段。架构文档 §5.4 定义了开源与商业化策略：核心包 MIT 开源，通过 PyPI 分发，GitHub 公开仓库，配合示例和文档作为增长引擎。

### 1.2 设计目标

- `pip install owlclaw` 一键安装核心 SDK
- `pip install owlclaw-mcp` 安装 MCP Server
- `pip install owlclaw[langchain]` 安装可选 LangChain 集成
- GitHub 仓库公开，README 清晰展示 30 分钟上手路径
- 语义版本控制（SemVer），自动化发布流程

---

## 2. 用户故事

### 2.1 作为业务开发者

**故事 1**：一键安装
```
作为业务开发者
我希望通过 pip install owlclaw 即可安装 OwlClaw SDK
这样我可以在 30 分钟内让业务系统获得 AI 自主能力
```

**验收标准**：
- [ ] `pip install owlclaw` 成功安装核心包（不拉入 LangChain 等可选依赖）
- [ ] `owlclaw --version` 输出正确版本号
- [ ] `owlclaw skill init --template monitoring my-skill` 可立即使用

**故事 2**：快速上手
```
作为业务开发者
我希望 README 和 examples 能让我 30 分钟内跑通第一个 Agent
这样我可以快速评估 OwlClaw 是否适合我的项目
```

**验收标准**：
- [ ] README 包含 Quick Start 章节（从安装到第一个 Agent Run）
- [ ] 至少 1 个最小示例可独立运行（不需要外部服务）
- [ ] 至少 2 个非交易场景示例（验证通用性）

### 2.2 作为开源贡献者

**故事 3**：清晰的贡献指南
```
作为潜在贡献者
我希望了解如何参与 OwlClaw 开发
这样我可以为项目贡献代码或 Skills
```

**验收标准**：
- [ ] CONTRIBUTING.md 包含开发环境搭建、测试运行、PR 规范
- [ ] 代码结构清晰，模块边界明确
- [ ] CI 通过是 PR 合并的前置条件

---

## 3. 功能需求

### 3.1 PyPI 发布

#### FR-1：包构建与发布

**需求**：使用 Poetry 构建 sdist 和 wheel，发布到 PyPI。

**验收标准**：
- [ ] `owlclaw` 核心包发布到 PyPI
- [ ] `owlclaw-mcp` 独立包发布到 PyPI
- [ ] 包元数据完整（description、author、license、keywords、classifiers）
- [ ] 支持可选依赖组：`owlclaw[langchain]`、`owlclaw[dev]`

#### FR-2：版本管理

**需求**：遵循语义版本控制（SemVer），通过 Git tag 管理版本。

**验收标准**：
- [ ] 版本格式：`MAJOR.MINOR.PATCH`（如 `0.1.0`）
- [ ] 版本号从 `pyproject.toml` 单一来源获取
- [ ] 每次发布创建 Git tag（如 `v0.1.0`）
- [ ] CHANGELOG.md 记录每个版本的变更

### 3.2 GitHub 发布

#### FR-3：仓库准备

**需求**：确保 GitHub 仓库公开前的合规性和质量。

**验收标准**：
- [ ] MIT LICENSE 文件存在且正确
- [ ] README.md 包含：项目定位、Quick Start、架构概览、对比表、贡献指南链接
- [ ] 无敏感信息泄露（.env、credentials、API keys 等）
- [ ] .gitignore 完整覆盖

#### FR-4：自动化发布流程

**需求**：通过 GitHub Actions 实现 tag-triggered 自动发布。

**验收标准**：
- [ ] Push `v*` tag 自动触发 CI → test → build → publish to PyPI
- [ ] 自动创建 GitHub Release（含 changelog）
- [ ] 发布失败时通知维护者

### 3.3 文档与示例

#### FR-5：发布文档

**需求**：确保发布时文档完整。

**验收标准**：
- [ ] README.md（英文，面向 GitHub/PyPI）
- [ ] docs/ 目录包含架构文档、API 参考、迁移指南
- [ ] examples/ 目录包含可独立运行的示例
- [ ] CONTRIBUTING.md 贡献指南
- [ ] CHANGELOG.md 变更日志

#### FR-6：社区反馈收集

**需求**：建立社区反馈渠道。

**验收标准**：
- [ ] GitHub Issues 模板（Bug Report、Feature Request）
- [ ] GitHub Discussions 启用
- [ ] 评估是否需要 Temporal 支持（基于社区需求）

---

## 4. 非功能需求

**NFR-1**：`pip install owlclaw` 安装时间 < 30s（不含网络延迟）  
**NFR-2**：核心包大小 < 5MB（不含可选依赖）  
**NFR-3**：支持 Python ≥ 3.10

---

## 5. 验收标准总览

### 5.1 功能验收
- [ ] **FR-1**：owlclaw 和 owlclaw-mcp 在 PyPI 可安装
- [ ] **FR-2**：版本号正确，Git tag 和 PyPI 版本一致
- [ ] **FR-3**：GitHub 仓库无敏感信息，README 完整
- [ ] **FR-4**：自动化发布流程可用
- [ ] **FR-5**：文档齐全
- [ ] **FR-6**：社区反馈渠道建立

### 5.2 测试验收
- [ ] 在干净环境中 `pip install owlclaw` 成功
- [ ] 安装后 `owlclaw --version` 和 `owlclaw skill list` 正常工作
- [ ] examples/ 中的示例可独立运行

---

## 6. 依赖

### 6.1 前置条件
- Phase 1 MVP 核心模块全部完成并验收
- 至少 2 个非交易场景示例（examples spec）
- CI 流程就绪（ci-setup spec）

### 6.2 外部依赖
- PyPI 账号和 API token
- GitHub Actions secrets 配置

---

## 7. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.4 开源与商业化策略
- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §6 MVP 范围定义
- [CI Setup Spec](../ci-setup/)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
