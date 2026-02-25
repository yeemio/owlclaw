# 任务清单：repo-hygiene（仓库卫生清理）

## 文档联动

- requirements: `.kiro/specs/repo-hygiene/requirements.md`
- design: `.kiro/specs/repo-hygiene/design.md`
- tasks: `.kiro/specs/repo-hygiene/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

## Tasks

### Phase 1：.gitignore 补充（P0，最优先）

- [x] **Task 1**: 补充 .gitignore 缺失条目
  - [x] 1.1 添加 Windows artifacts：`nul`
  - [x] 1.2 添加 IDE 文件：`*.code-workspace`
  - [x] 1.3 添加测试产物：`htmlcov/`、`.coverage`、`coverage.xml`
  - [x] 1.4 添加临时目录：`tmp/`、`temp/`
  - [x] 1.5 验证：`git check-ignore -v nul owlclaw.code-workspace htmlcov/` 均有输出
  - _Requirements: AC-5_

### Phase 2：根目录清理（P0）

- [x] **Task 2**: 删除 nul 文件
  - [x] 2.1 确认 `nul` 文件存在且为 Windows 误创建（0 字节或无意义内容）
  - [x] 2.2 执行 `git rm --cached nul` + 物理删除（若已 tracked）或直接删除
  - [x] 2.3 验证：根目录无 `nul` 文件
  - _Requirements: AC-2_

- [x] **Task 3**: 处理游离目录
  - [x] 3.1 检查 `rules/`、`ISSUE_TEMPLATE/`、`workflows/` 目录来源
        （可能是 git worktree 残留或 IDE 误创建）
  - [x] 3.2 若为 git worktree 残留：`git worktree prune` 清理
  - [x] 3.3 若为 IDE 误创建：删除并加入 .gitignore
  - [x] 3.4 验证：`git status` 无游离目录
  - _Requirements: AC-2_

### Phase 3：文档补充（P1）

- [x] **Task 4**: scripts/README.md
  - [x] 4.1 创建 `scripts/README.md`，列出每个脚本的用途、用法、依赖
  - [x] 4.2 标注哪些脚本是 CI 使用，哪些是本地开发使用
  - _Requirements: AC-4_

- [ ] **Task 5**: deploy/README.md 更新
  - [x] 5.1 更新 `deploy/README.md`：添加状态列（推荐/备用/废弃）
  - [ ] 5.2 指向根目录 compose 文件作为首选入口（local-devenv spec 完成后）
  - [x] 5.3 `deploy/README.langfuse.md` 更新：说明 Langfuse 通过官方镜像启动，
        不需要 clone 源码；引用 `docker-compose.dev.yml`
  - _Requirements: AC-3_

### Phase 4：docs/ 文件名检查（P1）

- [x] **Task 6**: docs/ 文件名可访问性验证
  - [x] 6.1 列出 `docs/` 所有文件，检查截断的文件名（Windows 路径长度限制）
  - [x] 6.2 `OWLHUB_CLI_NAMING_DECISION_PROPOSAL` 和 `OWLHUB_PHASE3_DB_DECISION_PROPOSAL`
        等截断文件名：确认完整文件名，必要时重命名
  - [x] 6.3 `ZERO_CODE_FASTPATH_DECISION_PROPOSAL` 同上
  - [x] 6.4 验证：所有 docs/ 文件在 Linux/macOS 下可正常访问（文件名无特殊字符）
  - _Requirements: AC-6_

### Phase 5：验收（P0）

- [ ] **Task 7**: 最终验收
  - [ ] 7.1 `git status` 在干净工作目录下无意外 untracked files
  - [ ] 7.2 根目录只有预期文件（无 `nul`、无游离目录）
  - [ ] 7.3 `git check-ignore -v .langfuse` 确认已 gitignore
  - [ ] 7.4 `scripts/README.md` 和 `deploy/README.md` 内容准确
  - [ ] 7.5 所有变更已 commit（`git log --oneline -5` 可见清理记录）
  - _Requirements: AC-1, AC-2, AC-3, AC-4, AC-5_

## Backlog

- [ ] `.editorconfig` 统一编辑器配置（缩进、换行符）
- [ ] `CODEOWNERS` 文件（指定各模块负责人）
- [ ] 根目录 `Makefile`（协同 local-devenv spec）
- [ ] `docs/` 目录 README（文档导航）

---

**维护者**: OwlClaw 核心团队
**最后更新**: 2026-02-25
