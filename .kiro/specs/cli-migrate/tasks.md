# Tasks: cli-migrate

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> **状态**：已完成  
> **最后更新**：2026-02-25

---

## 进度概览

- **总任务数**：24
- **已完成**：24
- **进行中**：0
- **未开始**：0

---

## Task 清单（24）

### 1. 命令入口与参数（3/3）
- [x] 1.1 提供 `owlclaw migrate scan` 命令分发
- [x] 1.2 支持 `--openapi`、`--orm`、`--output` 参数
- [x] 1.3 支持 `--output-mode handler|binding|both`

### 2. BindingGenerator（OpenAPI）（4/4）
- [x] 2.1 实现 `generate_from_openapi()`
- [x] 2.2 映射参数与 requestBody 到 `tools_schema.parameters`
- [x] 2.3 生成 HTTP binding（method/url/headers/response_mapping）
- [x] 2.4 security schemes -> `${ENV_VAR}` + prerequisites.env

### 3. BindingGenerator（ORM）（3/3）
- [x] 3.1 实现 `generate_from_orm()`
- [x] 3.2 生成参数化 SQL（`:param`）与 `parameter_mapping`
- [x] 3.3 默认 `read_only: true` 与连接环境变量引用

### 4. 扫描命令集成（3/3）
- [x] 4.1 `output_mode=binding` 生成 binding SKILL.md
- [x] 4.2 `output_mode=both` 同时生成 handler 与 binding
- [x] 4.3 支持 `--dry-run` 仅预览不写盘

### 5. Handler 实迁能力（3/3）
- [x] 5.1 复用 AST 扫描做 Python 候选函数扫描
- [x] 5.2 生成可执行 `@app.handler` 注册代码（`register_handlers(app)`）
- [x] 5.3 缺失类型注解输出 `MANUAL_REVIEW` 汇总

### 6. 报告与冲突处理（4/4）
- [x] 6.1 输出 JSON 迁移报告（统计+文件清单）
- [x] 6.2 输出 Markdown 迁移报告
- [x] 6.3 目标文件冲突检测 + `--force` 覆盖
- [x] 6.4 输出迁移统计（数量与预估工时）

### 7. 配置与向导（2/2）
- [x] 7.1 支持 `.owlclaw-migrate.yaml` 配置加载/校验
- [x] 7.2 实现交互式迁移向导 `owlclaw migrate init`

### 8. 测试与文档收口（2/2）
- [x] 8.1 单元测试覆盖：binding/scan/dry-run/report/conflict
- [x] 8.2 requirements/design 与 SPEC_TASKS_SCAN 进度对齐

---

## 阻塞项

- 无
