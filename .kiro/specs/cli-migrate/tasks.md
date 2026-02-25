# Tasks: cli-migrate

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> **状态**：进行中  
> **最后更新**：2026-02-25

---

## 进度概览

- **总任务数**：24
- **已完成**：12
- **进行中**：0
- **未开始**：12

---

## Task 清单

### 1. 命令入口与参数
- [x] 1.1 提供 `owlclaw migrate scan` 命令分发
- [x] 1.2 支持 `--openapi`、`--orm`、`--output` 参数
- [x] 1.3 支持 `--output-mode handler|binding|both` 并校验非法值

### 2. BindingGenerator（OpenAPI）
- [x] 2.1 实现 `generate_from_openapi()`
- [x] 2.2 映射 OpenAPI 参数与 requestBody 为 `tools_schema.parameters`
- [x] 2.3 生成 HTTP binding（method/url/headers/response_mapping）
- [x] 2.4 映射 security schemes 到 `${ENV_VAR}` + prerequisites.env
- [x] 2.5 生成内容可通过 `owlclaw skill validate`

### 3. BindingGenerator（ORM）
- [x] 3.1 实现 `generate_from_orm()`
- [x] 3.2 生成参数化 SQL 查询（`:param`）与 `parameter_mapping`
- [x] 3.3 默认 `read_only: true` 并输出连接环境变量引用
- [x] 3.4 生成内容可通过 `owlclaw skill validate`

### 4. 扫描命令集成
- [x] 4.1 `output_mode=binding` 生成 binding SKILL.md
- [x] 4.2 `output_mode=both` 同时生成 handler stub 与 binding SKILL.md
- [x] 4.3 OpenAPI/ORM 输入均可触发生成并输出生成路径

### 5. Handler 迁移能力（待完成）
- [ ] 5.1 Python 项目 AST 扫描（复用 cli-scan）产出候选函数清单
- [ ] 5.2 候选函数复杂度评估与优先级报告
- [ ] 5.3 基于函数签名生成可执行 `@app.handler` 注册代码（非 stub）
- [ ] 5.4 对缺失类型注解函数输出 `MANUAL_REVIEW` 汇总

### 6. 迁移报告与 dry-run（待完成）
- [ ] 6.1 输出 JSON + Markdown 迁移报告
- [ ] 6.2 实现 dry-run 预览（文件清单+内容摘要）
- [ ] 6.3 冲突检测（目标文件已存在）并给出可操作提示
- [ ] 6.4 输出迁移统计（文件数/代码行数/预估工作量）

### 7. 配置与向导（待完成）
- [ ] 7.1 支持 `.owlclaw-migrate.yaml` 配置加载
- [ ] 7.2 支持配置校验命令 `owlclaw migrate config validate`
- [ ] 7.3 实现交互式迁移向导 `owlclaw migrate init`
- [ ] 7.4 支持向导进度保存与恢复

### 8. 测试与文档收口（待完成）
- [ ] 8.1 补齐 handler 模式与 dry-run 的单元测试
- [ ] 8.2 增加端到端测试：scan -> generate -> validate -> load
- [ ] 8.3 requirements/design 同步更新为当前实现范围
- [ ] 8.4 更新 SPEC_TASKS_SCAN 的 cli-migrate 进度与检查点

---

## 阻塞项

- 无

