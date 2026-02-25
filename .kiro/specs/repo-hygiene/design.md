# 设计文档：repo-hygiene（仓库卫生清理）

## 1. 问题清单与处理方案

### 1.1 .langfuse/ 目录

**现状**：Langfuse 完整 Node.js 源码（含 `packages/`、`web/`、`worker/`、`pnpm-lock.yaml` 等）
物理存在于 `D:\AI\owlclaw\.langfuse\`，已被 `.gitignore` 排除，但仍污染工作目录。

**处理方案**：
- 确认 `.gitignore` 中 `.langfuse/` 条目有效（已验证：`git check-ignore -v .langfuse` 输出正确）
- 物理目录保留（gitignore 即可，不需要删除——这是用户本地的 Langfuse 安装）
- 在 `deploy/README.langfuse.md` 中说明：Langfuse 通过官方 docker compose 启动，
  不需要 clone 源码；`docker-compose.dev.yml` 中直接引用官方镜像

**不做**：强制删除 `.langfuse/`（可能是用户有意保留的本地 Langfuse 实例）

### 1.2 根目录游离文件/目录

**现状检查**（需在实现阶段确认）：
- `nul`：Windows 下 `> nul` 重定向误创建的文件，应删除
- `rules/`、`ISSUE_TEMPLATE/`、`workflows/`：可能是 git worktree 或 IDE 的游离产物
- `owlclaw.code-workspace`：VS Code workspace 文件，不应提交

**处理方案**：
```
删除：nul
加入 .gitignore：*.code-workspace、owlclaw.code-workspace
确认来源后处理：rules/、ISSUE_TEMPLATE/、workflows/
```

### 1.3 .gitignore 补充

当前缺少的条目：
```gitignore
# Windows artifacts
nul

# IDE workspace files
*.code-workspace

# Test coverage
htmlcov/
.coverage
coverage.xml

# Hypothesis (property testing)
.hypothesis/

# Temporary files
tmp/
temp/

# Local development
*.local.yaml
*.local.yml
```

### 1.4 deploy/ 状态标注

每个 compose 文件的状态：

| 文件 | 状态 | 说明 |
|------|------|------|
| `docker-compose.lite.hatchet-only.yml` | ✅ 推荐（本机 PG 场景） | 保留，更新注释 |
| `docker-compose.lite.yml` | ⚠️ 备用（PG 镜像需更新） | 更新为 pgvector:pg16 |
| `docker-compose.prod.yml` | ✅ 生产 | 保留，更新 PG 镜像 |
| `docker-compose.cron.yml` | ⚠️ 需更新 PG 镜像 | 更新为 pgvector:pg16 |
| `docker-compose.owlhub-api.yml` | ✅ OwlHub API | 保留 |

### 1.5 scripts/ README

```markdown
# scripts/

| 脚本 | 用途 | 用法 |
|------|------|------|
| validate_examples.py | 验证 examples/ 目录结构和 SKILL.md 格式 | `python scripts/validate_examples.py` |
| owlhub_build_index.py | 构建 OwlHub index.json | `python scripts/owlhub_build_index.py` |
| owlhub_generate_site.py | 生成 OwlHub 静态站点 | `python scripts/owlhub_generate_site.py` |
| owlhub_release_gate.py | OwlHub 发布闸门检查 | `python scripts/owlhub_release_gate.py` |
| review_template.py | 生成 review 模板 | `python scripts/review_template.py` |
| test_queue_trigger.py | 测试 Queue trigger | `python scripts/test_queue_trigger.py` |
| test_template.py | 测试模板渲染 | `python scripts/test_template.py` |
| notify_trigger.sql | PostgreSQL NOTIFY 触发器 SQL | `psql -f scripts/notify_trigger.sql` |
```

## 2. 执行顺序

```
1. .gitignore 补充（最安全，先做）
2. nul 文件删除
3. owlclaw.code-workspace 加入 gitignore
4. 游离目录（rules/等）确认来源后处理
5. scripts/README.md 创建
6. deploy/README.md 更新
7. deploy/ compose 文件 PG 镜像更新（协同 local-devenv spec）
8. 验收：git status 干净
```

## 3. 验证方法

```bash
# 验证 .gitignore 有效
git status --short  # 应无意外 untracked files

# 验证 .langfuse/ 已 gitignore
git check-ignore -v .langfuse  # 应输出 .gitignore 行号

# 验证根目录整洁
ls -la  # 只有预期文件

# 验证 docs/ 文件名可访问
python -c "import os; [print(f) for f in os.listdir('docs')]"
```
