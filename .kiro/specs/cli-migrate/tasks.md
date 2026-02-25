# Tasks: cli-migrate（scan/binding MVP）

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> 状态：已完成（24/24）  
> 最后更新：2026-02-25

---

## 任务清单（24）

### A. CLI 与参数分发

- [x] 1. 增加 `owlclaw migrate` 命令分发入口（`owlclaw/cli/__init__.py`）
- [x] 2. 增加 `migrate scan` 子命令路由
- [x] 3. 支持 `--openapi` 输入
- [x] 4. 支持 `--orm` 输入
- [x] 5. 支持 `--output/--path` 输出目录参数
- [x] 6. 支持 `--output-mode`（`handler|binding|both`）
- [x] 7. 增加 `migrate scan --help` 文本输出

### B. OpenAPI/ORM 扫描与转换

- [x] 8. 实现 OpenAPI 文件加载（YAML/JSON）
- [x] 9. 提取 endpoints（method/path/operationId/parameters/requestBody/responses）
- [x] 10. 解析 security schemes 并传递到生成器
- [x] 11. 实现 ORM 操作描述加载
- [x] 12. 解析 ORM operation（model/table/columns/filters/connection_env）

### C. BindingGenerator（核心）

- [x] 13. 新增 `BindingGenerator` 类（`owlclaw/cli/migrate/generators/binding.py`）
- [x] 14. 实现 `generate_from_openapi()`
- [x] 15. 实现 `generate_from_orm()`
- [x] 16. 输出 HTTP binding（method/url/headers/response_mapping）
- [x] 17. 输出 SQL binding（参数化 query + `read_only: true`）
- [x] 18. 安全凭证统一转 `${ENV_VAR}` + `prerequisites.env`
- [x] 19. 生成 SKILL.md 正文业务规则占位段落

### D. 输出模式与文件生成

- [x] 20. `binding` 模式生成 SKILL.md
- [x] 21. `handler` 模式生成 handler stub
- [x] 22. `both` 模式同时生成两类产物

### E. 测试与验收

- [x] 23. 新增/通过单测：`test_binding_generator.py`
- [x] 24. 新增/通过单测：`test_migrate_scan_cli.py`

---

## 验收记录

- `poetry run pytest tests/unit/cli_migrate/test_binding_generator.py tests/unit/cli_migrate/test_migrate_scan_cli.py -q`
- 结果：通过

---

## 说明

- 当前 spec 收口口径是 `migrate scan` + Declarative Binding 输出链路。
- 更大范围的“全量 brownfield 迁移向导”能力保留在 requirements/design 的后续阶段扩展，不作为本轮收口前置条件。
