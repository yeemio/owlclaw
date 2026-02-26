# 行业 Skills 包 — 任务清单

> **Spec**: industry-skills
> **创建日期**: 2026-02-25

---

## Task 1: 包基础设施

- [ ] 1.1 定义 `package.yaml` 格式规范
- [ ] 1.2 实现 `owlclaw skill install` 对行业包的支持（目录级安装）
- [ ] 1.3 实现 `owlclaw skill configure` 连接配置引导
- [ ] 1.4 实现 `owlclaw skill search --industry` 行业过滤
- [ ] 1.5 单元测试：包安装 + 配置流程

## Task 2: 零售/电商行业包

- [ ] 2.1 编写 `retail/package.yaml` + `README.md`
- [ ] 2.2 编写 `inventory-alert/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 2.3 编写 `order-anomaly/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 2.4 编写 `promotion-monitor/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 2.5 验证所有 Skills 通过 `owlclaw skill validate`
- [ ] 2.6 验证 Lite Mode 下可加载

## Task 3: 制造业行业包

- [ ] 3.1 编写 `manufacturing/package.yaml` + `README.md`
- [ ] 3.2 编写 `equipment-maintenance/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 3.3 编写 `production-scheduling/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 3.4 编写 `quality-inspection/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 3.5 验证所有 Skills 通过 `owlclaw skill validate`
- [ ] 3.6 验证 Lite Mode 下可加载

## Task 4: 金融/财务行业包

- [ ] 4.1 编写 `finance/package.yaml` + `README.md`
- [ ] 4.2 编写 `receivables-collection/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 4.3 编写 `expense-review/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 4.4 编写 `cashflow-alert/SKILL.md` + `BINDING_TEMPLATE.yaml`
- [ ] 4.5 验证所有 Skills 通过 `owlclaw skill validate`
- [ ] 4.6 验证 Lite Mode 下可加载

## Task 5: OwlHub 集成

- [ ] 5.1 将行业包目录纳入 OwlHub 仓库结构
- [ ] 5.2 更新 OwlHub index.json 包含行业包
- [ ] 5.3 验证 `owlclaw skill search --industry` 可发现行业包
