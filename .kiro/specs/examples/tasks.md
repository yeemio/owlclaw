# Tasks: examples（示例应用）

## 文档联动

- requirements: `.kiro/specs/examples/requirements.md`
- design: `.kiro/specs/examples/design.md`
- tasks: `.kiro/specs/examples/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`

> 状态：已完成（12/12）  
> 最后更新：2026-02-25

---

## 任务清单（12）

- [x] 1. 建立示例索引文档并列出可运行目录（`examples/README.md`）
- [x] 2. 提供非交易场景示例集（`examples/cron/`）
- [x] 3. 提供 LLM 集成示例集（`examples/integrations_llm/`）
- [x] 4. 提供 LangChain 集成示例集（`examples/langchain/`）
- [x] 5. 提供 Declarative Binding HTTP 示例（`examples/binding-http/`）
- [x] 6. 提供 OpenAPI -> binding 端到端示例（`examples/binding-openapi-e2e/`）
- [x] 7. 提供业务 Skills 示例（至少 3 个行业方向，`examples/owlhub_skills/`）
- [x] 8. 新增 mionyee 完整接入示例目录（`examples/mionyee-trading/`）
- [x] 9. 补齐 mionyee 示例身份文档（`docs/SOUL.md`、`docs/IDENTITY.md`）
- [x] 10. 补齐 mionyee 三个核心技能（entry-monitor / morning-decision / knowledge-feedback）
- [x] 11. 增加示例验收测试（`tests/unit/test_examples_mionyee.py`）
- [x] 12. 通过示例相关回归测试（langchain/examples/owlhub-skills/mionyee）

---

## 验收记录

- `poetry run pytest tests/unit/test_examples_mionyee.py tests/unit/integrations/test_langchain_examples.py tests/unit/test_owlhub_example_skills.py -q`
- 结果：通过

---

## 说明

- examples 的交付口径采用“可运行示例 + 可验证测试 + 索引文档”。
- 与生产部署相关内容不在本 spec 中收口，统一由 release/owlhub 的发布流程处理。
