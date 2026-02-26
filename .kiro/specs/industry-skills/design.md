# 行业 Skills 包 — 设计文档

> **Spec**: industry-skills
> **创建日期**: 2026-02-25

---

## 设计决策

### D-1: Skills 包格式

行业 Skills 包是 OwlHub 仓库中的目录，遵循统一结构：

```
owlhub/industry/{industry_name}/
├── package.yaml              # 包元数据（名称、版本、行业、依赖）
├── README.md                 # 行业说明 + 安装指南
└── {skill_name}/
    ├── SKILL.md              # 完整 SKILL.md
    └── BINDING_TEMPLATE.yaml # 连接模板
```

`package.yaml` 示例：

```yaml
name: retail-skills
version: 1.0.0
industry: retail
description: 零售/电商行业 Agent Skills 包
skills:
  - inventory-alert
  - order-anomaly
  - promotion-monitor
requires:
  owlclaw: ">=1.0.0"
```

### D-2: SKILL.md 双模式设计

每个行业 Skill 的 SKILL.md 同时包含自然语言描述和 `owlclaw:` 扩展字段：

```markdown
---
name: inventory-alert
description: 监控库存水平，低于安全线时自动预警
owlclaw:
  trigger:
    type: cron
    expression: "0 9 * * 1-5"
  binding:
    type: http
    endpoint: "${INVENTORY_API_URL}/levels"
    method: GET
---

# 库存预警

每个工作日早上 9 点检查一次库存。如果有商品的库存低于安全线，生成预警报告：
- 列出所有低于安全线 120% 的商品
- 按紧急程度排序（A 类 > B 类 > C 类）
- 建议补货数量 = 过去 30 天日均销量 × 7 天安全库存天数
- 周五的建议补货数量额外加 3 天

## 异常处理
- 库存 API 不可用时：记录告警，下次 Heartbeat 重试
- 数据缺失时：跳过该商品，在报告中标注"数据缺失"
```

这样的设计让：
- 业务人员可以只看自然语言部分理解 Skill 做什么
- Agent 可以使用 `owlclaw:` 字段精确执行
- 支持 skill-dx spec 的自然语言解析模式（忽略 `owlclaw:` 字段也能工作）

### D-3: BINDING_TEMPLATE.yaml

连接模板让用户只需填入自己的 endpoint：

```yaml
connections:
  inventory_api:
    type: http
    base_url: "${INVENTORY_API_URL}"
    auth:
      type: bearer
      token: "${INVENTORY_API_TOKEN}"
  notification:
    type: http
    base_url: "${NOTIFICATION_WEBHOOK_URL}"
    method: POST
```

`owlclaw skill configure` 命令引导用户填入环境变量值。

### D-4: 行业选择依据

| 行业 | 选择理由 |
|------|---------|
| 零售/电商 | 库存/订单是最直观的业务场景，几乎所有企业都有 |
| 制造业 | 设备维护/生产排程是高价值场景，Agent 自主决策价值大 |
| 金融/财务 | 应收催收/费用审核是合规驱动场景，治理层价值突出 |

### D-5: 文件结构

```
owlhub/industry/
├── retail/
│   ├── package.yaml
│   ├── README.md
│   ├── inventory-alert/
│   ├── order-anomaly/
│   └── promotion-monitor/
├── manufacturing/
│   ├── package.yaml
│   ├── README.md
│   ├── equipment-maintenance/
│   ├── production-scheduling/
│   └── quality-inspection/
└── finance/
    ├── package.yaml
    ├── README.md
    ├── receivables-collection/
    ├── expense-review/
    └── cashflow-alert/
```

## 依赖

- `owlclaw/cli/skill.py`（`owlclaw skill install/search/configure`）
- `owlclaw/capabilities/skill_parser.py`（SKILL.md 解析）
- `owlclaw/capabilities/bindings/`（Declarative Binding 执行）
- spec: owlhub（OwlHub 仓库结构）

## 不做

- 不做行业数据集（Skills 描述业务规则，不包含训练数据）
- 不做行业特定的 Agent 模型微调
- 不做 ERP/CRM 厂商特定的 binding 适配（用通用 HTTP/SQL binding）
