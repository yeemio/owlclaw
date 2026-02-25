# Tasks: examples

## 文档联动

- requirements: `.kiro/specs/examples/requirements.md`
- design: `.kiro/specs/examples/design.md`
- tasks: `.kiro/specs/examples/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> **状态**：已完成  
> **最后更新**：2026-02-25

---

## 进度概览

- **总任务数**：12
- **已完成**：12
- **进行中**：0
- **未开始**：0

---

## Task 清单

### 1. 索引与目录规范
- [x] 1.1 校准 `examples/README.md` 的目录索引与真实路径一致
- [x] 1.2 增加自动化测试，校验索引中引用路径均存在

### 2. 非交易场景示例
- [x] 2.1 提供 Cron 场景示例（`examples/cron/`）
- [x] 2.2 提供 API/Binding 场景示例（`examples/binding-http/`）

### 3. 生态与行业示例
- [x] 3.1 提供 LangChain 集成示例（`examples/langchain/`）
- [x] 3.2 提供 3 个行业技能示例（`examples/owlhub_skills/`）

### 4. mionyee 完整接入示例
- [x] 4.1 新增 `examples/mionyee-trading/` 示例目录、入口与 README
- [x] 4.2 补齐三任务技能文档（entry-monitor / morning-decision / knowledge-feedback）
- [x] 4.3 增加自动化可运行性验证（执行示例脚本并断言输出）

### 5. 运行与CI集成
- [x] 5.1 提供示例批量可运行验证脚本（覆盖至少 cron/langchain/mionyee）
- [x] 5.2 将示例可运行验证接入 GitHub Actions

### 6. 文档收口
- [x] 6.1 requirements/design 文档对齐现有示例命名与目录
- [x] 6.2 为 mionyee 示例补充 mock vs production 差异说明
- [x] 6.3 更新 SPEC_TASKS_SCAN 的 examples 收口说明与验收快照

---

## 阻塞项

- 无
