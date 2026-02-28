# 内容营销启动 — 任务清单

> **Spec**: content-launch
> **阶段**: Phase 8.3
> **前置**: mionyee-governance-overlay + mionyee-hatchet-migration（需要真实数据）

---

## Task 0：Spec 文档与契约

- [x] 0.1 requirements.md / design.md / tasks.md 三层齐全
- [x] 0.2 与 SPEC_TASKS_SCAN.md Phase 8.3 对齐

## Task 1：Mionyee 案例数据收集

- [ ] 1.1 收集治理前后的 LLM 调用数据（费用、调用量、拦截次数）
- [ ] 1.2 收集调度迁移前后的任务执行数据（成功率、恢复时间）
- [ ] 1.3 整理数据为对比表格和图表
- [ ] 1.4 数据真实性确认（禁止编造）
  - 采集脚手架已就绪：`scripts/content/collect_mionyee_case_data.py`
  - 操作指引：`docs/content/mionyee-data-collection-guide.md`

## Task 2：第一篇技术文章

- [ ] 2.1 根据 Mionyee 数据选择文章方向（A/B/C）
- [ ] 2.2 编写文章草稿（英文版）
- [ ] 2.3 编写可运行代码示例（pip install owlclaw → 3 步上手）
- [ ] 2.4 代码示例可复现性验证
- [ ] 2.5 编写中文版（掘金/V2EX 用）
- [ ] 2.6 发布到 Reddit/HN（英文版）
- [ ] 2.7 发布到掘金/V2EX（中文版）

## Task 3：Mionyee 案例材料

- [ ] 3.1 编写案例文档（背景→方案→实施→结果）
- [ ] 3.2 附真实数据对比（before vs after）
- [ ] 3.3 案例可用于两个场景验证（技术文章素材 + 咨询附件）

## Task 4：咨询方案模板

- [x] 4.1 编写标准咨询方案模板（调研→方案→实施→交付→维护）
- [x] 4.2 模板参数化验证（替换客户名称/系统类型后仍可用）
- [x] 4.3 定价参考表（培训 / 项目实施 / 月维护）
- [x] 4.4 准备 3 个场景的方案变体（报表解读 / 客户跟进 / 库存预警）

## Task 5：验收

- [ ] 5.1 第一篇文章已发布到 ≥ 2 个渠道
- [ ] 5.2 文章代码示例可运行
- [ ] 5.3 Mionyee 案例材料完成
- [ ] 5.4 咨询方案模板完成且可参数化
