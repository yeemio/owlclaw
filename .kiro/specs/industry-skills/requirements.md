# 行业 Skills 包 — 需求文档

> **Spec**: industry-skills
> **创建日期**: 2026-02-25
> **目标**: 为 3-5 个行业提供开箱即用的 Skills 包，作为 OwlHub 生态飞轮的启动燃料
> **关联**: `docs/POSITIONING.md` §八 生态飞轮第 2 层

---

## 背景

POSITIONING.md 承诺的生态飞轮第 2 层：

> "用户发布 Skills → OwlHub 积累 → 同行业复用 → 接入门槛持续降低"

飞轮需要启动燃料——如果 OwlHub 上空空如也，没有用户会来。skill-templates spec 已完成了模板框架（5 类通用模板），但模板是骨架，不是可直接使用的 Skills。行业 Skills 包是**带 Declarative Binding、带业务规则、带触发配置的完整 SKILL.md 集合**，用户 `owlclaw skill install` 后配置连接信息即可使用。

## 功能需求

### FR-1: 行业覆盖

首批覆盖 3 个行业，每个行业 3-5 个 Skills：

**零售/电商**：
- 库存预警（低库存检测 + 补货建议）
- 订单异常检测（超时/退货率异常/大额订单审核）
- 促销效果监控（销量对比 + ROI 计算）

**制造业**：
- 设备维护预警（基于运行时间/故障率的预测性维护）
- 生产排程优化（订单优先级 + 产能匹配）
- 质检异常检测（不良率趋势 + 根因分析触发）

**金融/财务**：
- 应收账款催收（账龄分析 + 催收策略 + 升级规则）
- 费用报销审核（合规检查 + 异常检测 + 审批路由）
- 现金流预警（余额趋势 + 大额支出预警）

### FR-2: Skills 包结构

每个行业 Skills 包是一个目录：

```
owlhub/industry/retail/
├── README.md                           # 行业包说明
├── inventory-alert/
│   ├── SKILL.md                        # 完整的自然语言 + owlclaw 扩展
│   └── BINDING_TEMPLATE.yaml           # 连接模板（用户填入自己的 endpoint）
├── order-anomaly/
│   ├── SKILL.md
│   └── BINDING_TEMPLATE.yaml
└── promotion-monitor/
    ├── SKILL.md
    └── BINDING_TEMPLATE.yaml
```

### FR-3: 安装与配置流程

```bash
# 浏览行业 Skills
owlclaw skill search --industry retail

# 安装整个行业包
owlclaw skill install owlhub/industry/retail

# 配置连接信息
owlclaw skill configure inventory-alert --endpoint https://erp.company.com/api/v3
```

### FR-4: SKILL.md 质量标准

每个行业 Skill 必须满足：
- 自然语言描述清晰（业务人员可读懂）
- 包含 `owlclaw:` 扩展字段（触发配置 + binding 声明）
- 包含至少 3 条业务规则
- 包含异常处理规则（数据缺失、服务不可用时的降级策略）
- 通过 `owlclaw skill validate` 校验

### FR-5: 文档与示例

每个行业包附带：
- README.md：行业背景 + 使用场景 + 安装步骤
- 配置示例：常见 ERP/CRM 的连接配置模板
- 效果预期：Agent 启用后的预期业务价值

## 非功能需求

- Skills 包遵循 Agent Skills 规范（agentskills.io）
- Binding 模板使用 `${ENV_VAR}` 引用凭据，不硬编码
- 所有 Skills 可在 Lite Mode 下加载（mock binding）

## 验收标准

1. 3 个行业、每个行业至少 3 个 Skills，共 9+ 个完整 SKILL.md
2. 所有 Skills 通过 `owlclaw skill validate` 校验
3. `owlclaw skill install` 可安装行业包
4. 每个 Skill 在 Lite Mode 下可加载并被 Agent 识别
5. 行业包 README 清晰可读
