# Tasks: release

## 文档联动

- requirements: `.kiro/specs/release/requirements.md`
- design: `.kiro/specs/release/design.md`
- tasks: `.kiro/specs/release/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> **状态**：进行中  
> **最后更新**：2026-02-25

---

## 进度概览

- **总任务数**：20
- **已完成**：12
- **进行中**：0
- **未开始**：8

---

## Task 清单（20）

### 1. 打包元数据与构建资产（4/4）
- [x] 1.1 `pyproject.toml` 包元数据完整（name/version/description/license/classifiers）
- [x] 1.2 可选依赖组已配置（`langchain`、`dev`/group）
- [x] 1.3 CLI 入口点已配置（`owlclaw = "owlclaw.cli:main"`）
- [x] 1.4 `release.yml` 构建并上传分发包（wheel/sdist）

### 2. 发布文档与社区入口（4/4）
- [x] 2.1 README（英文）包含定位、快速开始、架构与示例链接
- [x] 2.2 `CONTRIBUTING.md` 存在且可指导贡献流程
- [x] 2.3 新增 `CHANGELOG.md`（v0.1.0 初始记录）
- [x] 2.4 新增 GitHub Issue 模板（bug/feature）

### 3. 仓库安全与配置检查（3/3）
- [x] 3.1 `.gitignore` 覆盖 `.env`/`dist`/`build`/缓存目录
- [x] 3.2 全仓敏感信息扫描并形成可追溯报告（`docs/release/SECURITY_SCAN_REPORT.md`）
- [x] 3.3 发布前凭据最小权限审计（`docs/release/CREDENTIAL_AUDIT.md`）

### 4. 自动化发布联调（0/3）
- [ ] 4.1 配置并验证 PyPI token（GitHub Secrets）
- [ ] 4.2 在 GitHub Actions 上完成一次 TestPyPI/正式发布演练
- [ ] 4.3 验证 GitHub Release 自动创建与附件可下载

### 5. 外部平台开关（0/2）
- [ ] 5.1 仓库公开配置（Public/Topics/Description）
- [ ] 5.2 启用 GitHub Discussions

### 6. 最终验收（0/3）
- [ ] 6.1 远程 `pip install owlclaw` 验证通过（非本地源码路径）
- [ ] 6.2 `owlclaw --version` 与 `owlclaw skill list` 在干净环境可运行
- [ ] 6.3 发布版本与 changelog、tag、release 三方一致

### 7. 预检自动化（新增本地收口）（1/1）
- [x] 7.1 新增发布前预检脚本（`scripts/release_preflight.py`）并可执行通过

---

## 阻塞项（外部依赖）

- PyPI token 与发布权限（需要仓库维护者提供）
- GitHub 仓库可见性/Discussions 开关（需要管理员权限）
- 干净环境在线安装依赖受网络 SSL 链路影响（需可用外网/镜像源后复验）
