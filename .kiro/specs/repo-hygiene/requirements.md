# 需求文档：repo-hygiene（仓库卫生清理）

## 背景

随着多轮并行开发，仓库积累了若干卫生问题：

1. **`.langfuse/` 目录污染**：Langfuse 完整源码（Node.js 全栈项目，数百 MB）被 clone 进仓库，
   虽已 gitignore 但物理存在，污染工作目录，影响搜索和工具性能
2. **`deploy/` compose 文件散乱**：5 个 compose 文件无统一入口，命名不一致，部分已过时
3. **根目录杂乱**：`nul`（Windows 误创建文件）、`rules/`、`ISSUE_TEMPLATE/`、`workflows/` 等
   游离目录出现在根目录（应在 `.github/` 下）
4. **`docs/` 文档缺口**：`ZERO_CODE_FASTPATH_DECISION_PROPOSAL` 等文件名截断（Windows 路径长度限制）
5. **`scripts/` 缺少 README**：脚本用途不明
6. **`.gitignore` 需要补充**：`nul`、`*.code-workspace`、本地开发产物等

## 目标

**仓库根目录整洁、文档可寻、工具搜索高效、新贡献者无困惑。**

## 用户故事

### US-1：根目录整洁
作为开发者，打开仓库根目录时，只看到标准的项目文件，
不看到游离的 `nul`、`rules/`、`ISSUE_TEMPLATE/` 等。

### US-2：.langfuse/ 不污染工作目录
作为开发者，`find . -name "*.py"` 或 IDE 搜索不会扫描到 Langfuse 的 Node.js 源码，
工具性能正常。

### US-3：deploy/ 结构清晰
作为运维人员，`deploy/README.md` 清晰说明每个 compose 文件的用途，
过时文件已标注或移除。

### US-4：scripts/ 有文档
作为开发者，`scripts/README.md` 说明每个脚本的用途和用法。

### US-5：.gitignore 完整
作为开发者，本地开发产物（`nul`、`*.code-workspace`、`htmlcov/`、`.env`）
不会意外被 git 追踪。

## 验收标准

### AC-1：.langfuse/ 处理
- [ ] `.langfuse/` 目录从工作目录移除或确认已完全 gitignore
- [ ] `.gitignore` 中 `.langfuse/` 条目正确（已有，验证）
- [ ] `deploy/README.langfuse.md` 说明如何本地启动 Langfuse（引用官方 docker compose）
- [ ] `docs/` 中补充 Langfuse 集成说明（引用 `config/langfuse.example.yaml`）

### AC-2：根目录清理
- [ ] `nul` 文件删除（Windows 误创建）
- [ ] 游离的 `rules/`、`ISSUE_TEMPLATE/`、`workflows/` 目录确认来源并处理
- [ ] `owlclaw.code-workspace` 加入 `.gitignore`（IDE 配置不应提交）
- [ ] 根目录只保留标准文件：`pyproject.toml`、`poetry.lock`、`README.md`、`LICENSE`、
      `CHANGELOG.md`、`CONTRIBUTING.md`、`AGENTS.md`、`alembic.ini`、
      `.env.example`、`.gitignore`、`.pre-commit-config.yaml`、`.releaserc.json`

### AC-3：deploy/ 整理
- [ ] `deploy/README.md` 更新：明确标注每个 compose 文件的状态（推荐/备用/废弃）
- [ ] 过时的 `docker-compose.cron.yml`（使用 `postgres:15-alpine`）标注废弃或更新
- [ ] `deploy/` 下 compose 文件顶部注释统一格式

### AC-4：scripts/ 文档
- [ ] 创建 `scripts/README.md`，列出每个脚本的用途、用法、依赖

### AC-5：.gitignore 完整
- [ ] 添加：`nul`、`*.code-workspace`、`htmlcov/`、`.hypothesis/`、`tmp/`
- [ ] 验证：`git status` 在干净工作目录下无意外的 untracked files

### AC-6：文档文件名修复
- [ ] 检查 `docs/` 下截断的文件名（Windows 路径限制导致），必要时重命名
- [ ] 确认所有 `docs/` 文件可在 Linux/macOS 正常访问

## 非功能需求

- 清理操作不破坏任何现有功能
- `.langfuse/` 处理方案不影响 Langfuse 集成功能（集成通过 pip 包，不依赖源码）
- 所有变更有对应的 git commit，便于回溯

## 范围外

- compose 文件内容重写（属于 local-devenv spec）
- 测试文件整理（属于 test-infra spec）
- CLI 命令面规划（推迟到功能全部完成后）
