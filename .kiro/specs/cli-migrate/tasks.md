# Tasks: 迁移工具

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **状态**：进行中（binding 输出模式已完成）  
> **预估工作量**：4-6 天  
> **最后更新**：2026-02-25  
> **执行原则**：本清单内所有任务均须专业、认真完成，不区分可选与必选（见规范 §1.4、§4.5）。

---

## 进度概览

- **总任务数**：24
- **已完成**：12（Task 4.1 / 4.2 / 4.3）
- **进行中**：0
- **未开始**：12

---

## 1. 需求与设计（1-2 天）

### 1.1 需求收敛
- [ ] 1.1.1 完成需求评审与范围确认
- [ ] 1.1.2 明确外部依赖与契约

### 1.2 设计落地
- [ ] 1.2.1 完成架构设计评审
- [ ] 1.2.2 明确集成点：何时、何处调用适配层

---

## 2. 实现与验证（2-4 天）

### 2.1 最小实现
- [ ] 2.1.1 实现核心能力与注册流程
- [ ] 2.1.2 完成最小端到端验证

---

## 3. 验收清单

### 3.1 功能验收
- [ ] 核心能力可被注册与调用
- [ ] 配置与约束生效

### 3.2 性能验收
- [ ] 关键路径无明显阻塞

### 3.3 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖核心场景

### 3.4 文档验收
- [ ] 文档完整

---

## 4. Binding 输出模式（与 declarative-binding spec 联动）

### 4.1 BindingGenerator 实现
- [x] 4.1.1 实现 BindingGenerator 类（与 HandlerGenerator/SKILLGenerator 并列）
- [x] 4.1.2 实现 `generate_from_openapi()`：OpenAPI endpoint → HTTP Binding SKILL.md
- [x] 4.1.3 实现 `generate_from_orm()`：ORM operation → SQL Binding SKILL.md
- [x] 4.1.4 实现 security schemes → `${ENV_VAR}` + prerequisites.env 映射
- [x] 4.1.5 实现 response schema → response_mapping 映射
- [x] 4.1.6 生成的 SKILL.md 通过 `owlclaw skill validate` 验证

### 4.2 CLI 集成
- [x] 4.2.1 扩展 `owlclaw migrate scan` 增加 `--output-mode` 参数（handler/binding/both）
- [x] 4.2.2 `--output-mode binding` 时调用 BindingGenerator
- [x] 4.2.3 `--output-mode both` 时同时生成 @handler 和 binding SKILL.md

### 4.3 测试
- [x] 4.3.1 单元测试：OpenAPI → HTTP Binding SKILL.md 生成
- [x] 4.3.2 单元测试：ORM → SQL Binding SKILL.md 生成
- [x] 4.3.3 集成测试：端到端 scan → generate → validate → load

---

## 5. 依赖与阻塞

### 5.1 依赖
- CLI 框架
- `declarative-binding` spec（Binding Schema 定义）
- `cli-scan` spec（AST 扫描器，PythonFunctionScanner 复用）

### 5.2 阻塞
- 无

---

## 6. 风险

### 5.1 风险描述
- **缓解**：引入契约与 Mock，CI 验证关键路径

---

## 7. 参考文档

- docs/ARCHITECTURE_ANALYSIS.md

---

**维护者**：平台研发  
**最后更新**：2026-02-25
